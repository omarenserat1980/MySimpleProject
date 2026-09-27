"""Machine-readable production health diagnostics."""
def diagnose(result):
 checks={k:result[k].get('status') for k in ('visual_qc','film_qc','final_qc') if isinstance(result.get(k),dict)}
 failures=[]
 if result.get('status') not in (None,'VERIFIED_COMPLETED','VERIFIED'): failures.append('factory_status')
 failures += [k for k,v in checks.items() if v not in ('VERIFIED','VERIFIED_COMPLETED')]
 return {'health':'HEALTHY' if not failures else 'DEGRADED','failures':failures,'checks':checks}
