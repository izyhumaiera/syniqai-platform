import sys
sys.path.insert(0, 'c:/Users/User/Desktop/SYNIQ/gui/api')

from SyniqAI_unstructured_package import QualityRulesEngine, MLModelRegistry, LLMService

print("=== SyniqAI Unstructured Package Status ===\n")

r = QualityRulesEngine()
print(f"[Rules Engine] PostgreSQL connected: {r._db_ok}")
rules = r.get_quality_rules()
print(f"[Rules Engine] Total rules in DB: {len(rules)}")
by_type = {}
for rule in rules:
    t = rule['media_type']
    by_type[t] = by_type.get(t, 0) + 1
for t, count in sorted(by_type.items()):
    print(f"  - {t}: {count} rules")

print()
reg = MLModelRegistry()
print(f"[ML Registry] PostgreSQL connected: {reg._db_ok}")
models = reg.get_all_models()
print(f"[ML Registry] Total models in DB: {len(models)}")
for m in models:
    print(f"  - [{m['category']}] {m['name']} ({m['framework']})")

vdbs = reg.get_vector_databases()
print(f"\n[ML Registry] Vector databases: {len(vdbs)}")
for v in vdbs:
    print(f"  - {v['name']} ({v['type']})")

print()
llm = LLMService()
print(f"[LLM Service] Provider  : {llm._provider}")
print(f"[LLM Service] API URL   : {llm._api_url or '(not set)'}")
import os
key = os.getenv("LLM_API_KEY", "")
if key and key != "sk-YOUR_OPENAI_API_KEY_HERE":
    print(f"[LLM Service] API Key   : {key[:8]}...{key[-4:]} (configured)")
    print("[LLM Service] Status    : REAL LLM ACTIVE")
else:
    print("[LLM Service] API Key   : (placeholder — fill in .env)")
    print("[LLM Service] Status    : Rule-based fallback")

print("\n=== All checks complete ===")
