"""
Test rover receiving corrections from base station
"""
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Handler, Framer
from sbp.navigation import SBP_MSG_BASELINE_NED, SBP_MSG_POS_LLH
import time

class RoverBaseTest:
    def __init__(self, base_host, base_port):
        self.base_host = base_host
        self.base_port = base_port
        self.corrections_received = 0
        self.positions_received = 0
        self.start_time = None
    
    def run_test(self, duration=120):
        """Run integration test"""
        
        print("="*60)
        print("ROVER-BASE INTEGRATION TEST")
        print(f"Base: {self.base_host}:{self.base_port}")
        print("="*60)
        
        self.start_time = time.time()
        
        try:
            with TCPDriver(self.base_host, self.base_port) as driver:
                with Handler(Framer(driver.read, None, verbose=False)) as source:
                    
                    print("\nConnected to base station")
                    print("Testing for", duration, "seconds...")
                    print("\nWaiting for messages...")
                    
                    for msg, metadata in source:
                        elapsed = time.time() - self.start_time
                        
                        if msg.msg_type == SBP_MSG_BASELINE_NED:
                            self.corrections_received += 1
                            if self.corrections_received == 1:
                                print(f"\n✅ FIRST CORRECTION RECEIVED at {elapsed:.1f}s")
                                print(f"   N:{msg.n:.3f}m E:{msg.e:.3f}m D:{msg.d:.3f}m")
                        
                        elif msg.msg_type == SBP_MSG_POS_LLH:
                            self.positions_received += 1
                            if self.positions_received == 1:
                                print(f"\n📍 FIRST POSITION at {elapsed:.1f}s")
                                print(f"   Lat:{msg.lat:.6f} Lon:{msg.lon:.6f} Alt:{msg.height:.2f}m")
                        
                        # Print status every 10 seconds
                        if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                            print(f"\n--- {int(elapsed)}s: "
                                  f"{self.corrections_received} corrections, "
                                  f"{self.positions_received} positions")
                        
                        if elapsed >= duration:
                            break
                    
        except Exception as e:
            print(f"\n❌ Connection error: {e}")
            return False
        
        # Generate test report
        return self.generate_report(duration)
    
    def generate_report(self, duration):
        """Generate test report"""
        
        elapsed = time.time() - self.start_time
        
        print("\n" + "="*60)
        print("INTEGRATION TEST REPORT")
        print("="*60)
        
        print(f"\nTest Duration: {elapsed:.1f} seconds")
        print(f"Corrections Received: {self.corrections_received}")
        print(f"Positions Received: {self.positions_received}")
        
        if self.corrections_received > 0:
            correction_rate = self.corrections_received / elapsed
            print(f"Correction Rate: {correction_rate:.2f} Hz")
            
            if correction_rate >= 1.0:
                print("\n✅ PASS: Good correction rate (>1 Hz)")
            elif correction_rate >= 0.5:
                print("\n⚠️  WARNING: Low correction rate (<1 Hz)")
            else:
                print("\n❌ FAIL: Very low correction rate")
        else:
            print("\n❌ FAIL: No corrections received")
        
        if self.positions_received > 0:
            position_rate = self.positions_received / elapsed
            print(f"Position Rate: {position_rate:.2f} Hz")
        else:
            print("ℹ️  No position messages received (may be normal)")
        
        print("\nOverall Status:", end=" ")
        if self.corrections_received >= 10 and self.corrections_received / elapsed >= 0.5:
            print("✅ SUCCESS - Rover can receive corrections")
        elif self.corrections_received > 0:
            print("⚠️  PARTIAL - Some corrections received")
        else:
            print("❌ FAIL - No corrections received")
        
        return self.corrections_received > 0

if __name__ == "__main__":
    test = RoverBaseTest("195.37.48.235", 55555)
    success = test.run_test(duration=60)
    
    if success:
        print("\n🎉 Rover-base communication is WORKING!")
    else:
        print("\n🔧 Check rover configuration and base station settings")