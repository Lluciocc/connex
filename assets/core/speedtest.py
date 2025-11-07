#!/usr/bin/env python3
"""
Custom speedtest module for connex
Simple implementation without external dependencies
"""
import socket
import time
import urllib.request
import urllib.error
import threading
from typing import Optional, Callable, Dict

class SpeedTest:
    """Custom speed test implementation"""
    
    # Test servers 
    DOWNLOAD_URLS = [
        #"https://speed.hetzner.de/100MB.bin", # 100MB file
        "http://speedtest.tele2.net/10MB.zip",
        "http://proof.ovh.net/files/10Mb.dat",
        "http://ipv4.download.thinkbroadband.com/10MB.zip",
    ]
    
    # Upload test server
    UPLOAD_URL = "https://httpbin.org/post"
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize speedtest
        callback: function(stage, progress, message) to report progress
        """
        self.callback = callback
        self.results = {
            'ping': 0.0,
            'download': 0.0,
            'upload': 0.0,
            'server': '',
            'error': None
        }
        self._cancelled = False
    
    def cancel(self):
        """Cancel ongoing test"""
        self._cancelled = True
    
    def _report(self, stage: str, progress: float, message: str):
        """Report progress to callback"""
        if self.callback:
            self.callback(stage, progress, message)
    
    def test_ping(self, host: str = "8.8.8.8", port: int = 53, timeout: int = 3) -> float:
        """
        Test ping latency to a host
        Returns latency in milliseconds
        """
        if self._cancelled:
            return 0.0
        
        self._report("ping", 0.1, "Testing latency...")
        
        try:
            # Resolve DNS first
            start = time.time()
            socket.gethostbyname(host)
            dns_time = (time.time() - start) * 1000
            
            # TCP connection test
            times = []
            for i in range(3):
                if self._cancelled:
                    break
                
                start = time.time()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                
                try:
                    sock.connect((host, port))
                    elapsed = (time.time() - start) * 1000
                    times.append(elapsed)
                except (socket.timeout, socket.error):
                    pass
                finally:
                    sock.close()
                
                self._report("ping", 0.1 + (i + 1) * 0.05, f"Ping test {i+1}/3...")
            
            if times:
                avg_ping = sum(times) / len(times)
                self.results['ping'] = round(avg_ping, 2)
                return self.results['ping']
            else:
                self.results['ping'] = 0.0
                return 0.0
        
        except Exception as e:
            self.results['error'] = f"Ping test failed: {str(e)}"
            return 0.0
    
    def test_download(self, size_mb: int = 10, timeout: int = 30) -> float:
        """
        Test download speed
        Returns speed in Mbps
        """
        if self._cancelled:
            return 0.0
        
        self._report("download", 0.3, "Testing download speed...")
        
        best_speed = 0.0
        best_server = ""
        
        for i, url in enumerate(self.DOWNLOAD_URLS):
            if self._cancelled:
                break
            
            try:
                self._report("download", 0.3 + i * 0.1, f"Testing server {i+1}...")
                
                start_time = time.time()
                downloaded = 0
                
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'connex/1.0')
                
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    chunk_size = 8192
                    while True:
                        if self._cancelled:
                            break
                        
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        
                        downloaded += len(chunk)
                        
                        # Update progress
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed_mbps = (downloaded * 8) / (elapsed * 1_000_000)
                            progress = min(0.3 + i * 0.1 + 0.05, 0.6)
                            self._report("download", progress, 
                                       f"Download: {speed_mbps:.2f} Mbps")
                
                elapsed = time.time() - start_time
                
                if elapsed > 0 and downloaded > 0:
                    speed_mbps = (downloaded * 8) / (elapsed * 1_000_000)
                    
                    if speed_mbps > best_speed:
                        best_speed = speed_mbps
                        best_server = url.split('/')[2]
                
                continue
            
            except (urllib.error.URLError, socket.timeout) as e:
                continue
            except Exception as e:
                continue
        
        self.results['download'] = round(best_speed, 2)
        self.results['server'] = best_server
        return self.results['download']
    
    def test_upload(self, size_kb: int = 1024, timeout: int = 30) -> float:
        """
        Test upload speed
        Returns speed in Mbps
        """
        if self._cancelled:
            return 0.0
        
        self._report("upload", 0.7, "Testing upload speed...")
        
        try:
            # Generate random data
            data = b'0' * (size_kb * 1024)
            
            start_time = time.time()
            
            req = urllib.request.Request(self.UPLOAD_URL, data=data, method='POST')
            req.add_header('User-Agent', 'connex/1.0')
            req.add_header('Content-Type', 'application/octet-stream')
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response.read()
            
            elapsed = time.time() - start_time
            
            if elapsed > 0:
                speed_mbps = (len(data) * 8) / (elapsed * 1_000_000)
                self.results['upload'] = round(speed_mbps, 2)
                self._report("upload", 0.9, f"Upload: {speed_mbps:.2f} Mbps")
                return self.results['upload']
        
        except Exception as e:
            self.results['error'] = f"Upload test failed: {str(e)}"
            return 0.0
        
        return 0.0
    
    def run_full_test(self) -> Dict:
        """
        Run complete speed test (ping + download + upload)
        Returns dict with results
        """
        try:
            self._report("init", 0.0, "Initializing test...")
            
            # Test ping
            self.test_ping()
            
            if self._cancelled:
                self.results['error'] = "Test cancelled"
                return self.results
            
            # Test download
            #self.test_download(size_mb=100)
            self.test_download()
            
            if self._cancelled:
                self.results['error'] = "Test cancelled"
                return self.results
            
            # Test upload
            #self.test_upload() # I don't like it for now. 
            
            self._report("complete", 1.0, "Test complete!")
            
        except Exception as e:
            self.results['error'] = str(e)
        
        return self.results


# CLI test function
def cli_speedtest():
    """Run speedtest from command line"""
    def progress_callback(stage, progress, message):
        bar_length = 30
        filled = int(bar_length * progress)
        bar = '█' * filled + '░' * (bar_length - filled) # VERY VERY COOL OMG
        print(f"\r[{bar}] {progress*100:.0f}% - {message}", end='', flush=True)
    
    print("connex - SpeedTest")
    print("=" * 50)
    
    test = SpeedTest(callback=progress_callback)
    results = test.run_full_test()
    
    print("\n\n" + "=" * 50)
    print("Results:")
    print("=" * 50)
    
    if results['error']:
        print(f"Error: {results['error']}")
        return 1
    
    print(f"Server: {results['server'] or 'N/A'}")
    print(f"Ping: {results['ping']:.1f} ms")
    print(f"Download: {results['download']:.2f} Mbps")
    
    if results['upload'] > 0:
        print(f"Upload: {results['upload']:.2f} Mbps")
    
    print("=" * 50)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(cli_speedtest())