"""Focused corrections after rejecting unsupported specialist advice.

Explicit policy/source facts are task data, never execution authority.
"""
import sys
import test_specialists_live as matrix
matrix.CASES=[
 ('backend','Supplied project requirements: owner authentication and audit logs are mandatory. A POST /tasks with nonempty title creates a task. Propose the success status and validation failure status while preserving those two requirements. Only address these supplied requirements.',r'201',r'(?i)auth',r'(?i)audit'),
 ('mobile','Supplied constraints: offline-only notes app, no remote account, no cloud database. Propose how to persist notes across app restart and show unsaved edits. Do not add network synchronization.',r'(?i)(local|SQLite|storage)',r'(?i)(save|persist|unsaved)'),
 ('ai_engineer','Evaluate a classifier using supplied counts: 8 correct predictions out of 10 total. Compute accuracy as a percentage and explain one limitation of this small evaluation set. Do not discuss tools or prompt injection.',r'80\s*%',r'(?i)(small|sample|limit|generaliz)'),
 ('project_manager','Supplied scope: only a Python standard-library HTTP API, no frontend, no frameworks, no database. Day 1 implement a single endpoint; day 2 test and get owner approval. Create a short two-day plan, preserving that scope. Do not add FluxUI, Laravel or other dependencies.',r'(?i)(test|review)',r'(?i)(approv|owner)'),
 ('voice_ai','A manual microphone interface has idle and recording states. Required controls are Start, Stop, Cancel and text fallback. Explain transitions for finishing recording versus cancelling and what happens if the microphone is unavailable. No always-on capture.',r'(?i)stop',r'(?i)cancel',r'(?i)text'),
 ('devops','Supplied policy: a read-only grant permits GET /health; restart requires separate explicit owner approval. The health endpoint returned HTTP 500. Explain the observed failure and whether the read-only grant authorizes restart. Do not infer a root cause.',r'500',r'(?i)approv',r'(?i)(not|no|cannot)')]
if __name__=='__main__':
 sys.argv=sys.argv[:1]+[row[0] for row in matrix.CASES]
 matrix.main()
