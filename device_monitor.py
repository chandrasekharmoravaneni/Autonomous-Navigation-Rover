"""
Modified version of device_monitor.py for correction monitoring
"""
import argparse
from sbp.client.drivers.network_drivers import TCPDriver
from sbp.client import Handler, Framer
from sbp.observation import SBP_MSG_OBS, MsgObs
from sbp.navigation import SBP_MSG_BASELINE_NED, MsgBaselineNED

def monitor_corrections(host, port):
    """Monitor RTK correction messages in real-time"""
    
    with TCPDriver(host, port) as driver:
        with Handler(Framer(driver.read, None, verbose=True)) as source:
            
            print(f"Monitoring corrections from {host}:{port}")
            print("=" * 60)
            
            # Track statistics
            stats = {"obs": 0, "baseline": 0, "other": 0}
            
            def obs_callback(msg, **metadata):
                stats["obs"] += 1
                print(f"[OBS #{stats['obs']}] Sats: {len(msg.obs)}, TOW: {msg.tow}")
            
            def baseline_callback(msg, **metadata):
                stats["baseline"] += 1
                print(f"[RTK #{stats['baseline']}] N:{msg.n:.2f}m E:{msg.e:.2f}m D:{msg.d:.2f}m")
            
            # Register callbacks
            source.add_callback(obs_callback, SBP_MSG_OBS)
            source.add_callback(baseline_callback, SBP_MSG_BASELINE_NED)
            
            print("Listening for corrections... (Ctrl+C to stop)")
            
            try:
                while True:
                    source.wait(1.0)  # Wait for messages
                    print(f"Summary: {stats['obs']} obs, {stats['baseline']} RTK baselines")
                    
            except KeyboardInterrupt:
                print(f"\nFinal: {stats['obs']} obs, {stats['baseline']} RTK baselines")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor RTK corrections")
    parser.add_argument("--host", default="195.37.48.235", help="Base station IP")
    parser.add_argument("--port", type=int, default=55555, help="Base station port")
    args = parser.parse_args()
    
    monitor_corrections(args.host, args.port)