"""Reproduce the final fifteen scoped tasks; no mocked specialist responses."""
import sys
import test_specialists_live as matrix
import test_specialist_corrections_live as first
# Importing correction tables does not invoke inference.
first_cases=list(matrix.CASES)
import test_specialist_final_corrections_live as final
final_cases=list(matrix.CASES)
import test_voice_specialist_controls_live as voice
voice_cases=list(matrix.CASES)
# Reload the baseline table; context mappings are explicit and bounded.
import importlib
importlib.reload(matrix)
roles={case[0]:case for case in matrix.CASES}
roles.update({case[0]:case for case in first_cases if case[0] in ('mobile','ai_engineer')})
roles.update({case[0]:case for case in final_cases+voice_cases})
matrix.CASES=list(roles.values())
if __name__=='__main__':
 if sys.argv[1:]==['--list']:
  import json
  print(json.dumps([{'role':row[0],'prompt':row[1]} for row in matrix.CASES],indent=2))
 else:matrix.main()
