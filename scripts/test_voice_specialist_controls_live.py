"""Explicit four-control voice contract; real inference, no microphone claim."""
import sys
import test_specialists_live as matrix
matrix.CASES=[('voice_ai','Design a manual push-to-talk interface. Return exactly four short lines labelled Start, Stop, Cancel, and Unavailable microphone. Specify that Stop finalizes recording, Cancel discards audio, and unavailable microphone offers manual text input. No automatic recording or placeholder transcript.',r'(?i)stop',r'(?i)cancel',r'(?i)discard',r'(?i)text')]
if __name__=='__main__':sys.argv=sys.argv[:1]+['voice_ai'];matrix.main()
