import sys
sys.path.insert(0, '.')

from fuzzy_decision_engine import get_fuzzy_engine
from isr_precheck import get_isr_engine
from interceptor_chain import get_interceptor_chain
from quantum_jammer import get_quantum_jammer
from cyber_takeover import get_cyber_system
from weapons_system import weapons_engine

print("[OK] All 5 new modules + weapons_engine loaded")

# ISR test
ie = get_isr_engine()
r  = ie.quick_isr(speed_kmh=120, distance_km=2.5)
print(f"[OK] ISR @ 120km/h, 2.5km: {r:.1f}%")

# Fuzzy test
fe = get_fuzzy_engine()
fr = fe.evaluate({
    "distance":3,"speed":120,"altitude":200,"rcs":1.0,
    "cam_conf":75,"obj_size":55,"rf_strength":65,
    "rf_risk":60,"acoustic":0,"movement":70
})
lvl   = fr["threat_level"]
score = fr["threat_score"]
print(f"[OK] Fuzzy: {lvl} ({score:.0f}%)")

# Weapons status
ws = weapons_engine.system_status()
print(f"[OK] Weapons status: {ws}")

# Cyber test
cs = get_cyber_system()
cr = cs.execute("T-999", rf_strength=75, distance_m=800)
print(f"[OK] Cyber: {cr['overall_status']} mode={cr['takeover_mode']}")

# Quantum test
qj = get_quantum_jammer()
qr = qj.jam("T-999", distance_m=1500, fhss_pattern="DJI_OCUSYNC")
print(f"[OK] Quantum: {qr['status']} eff={qr['effectiveness_pct']:.0f}%")

# Chain test
ic = get_interceptor_chain()
chained = ic.run_chain(
    target_id="T-999",
    target_speed_kmh=80,
    target_distance_km=2.0,
    target_bearing_deg=45,
    async_dispatch=False,
)
print(f"[OK] Chain: {chained['final_status']}")

print("\n[PASS] MCDIS v2.0 full integration test complete.")
