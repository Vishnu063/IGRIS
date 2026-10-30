"""Private INR ledger of operator-recorded events, not a bank/payment connector."""
from contextlib import contextmanager
import sqlite3
from uuid import uuid4

from .guardian.policy import Denied, Policy
from .memory import knowledge_text, private_file
from .opportunities import nonnegative_int

STAGES = ('found', 'proposal_submitted', 'client_acquired', 'project_completed')


class Earnings:
    def __init__(self, path, owner, *, initialize=False):
        self.path = private_file(path, create=initialize)
        self.owner = Policy(owner).actor
        if initialize:
            with self._db() as db:
                db.executescript('''
                    CREATE TABLE deals(id TEXT PRIMARY KEY, title TEXT, estimate INTEGER, state TEXT, evidence TEXT);
                    CREATE TABLE invoices(id TEXT PRIMARY KEY, deal TEXT, amount INTEGER);
                    CREATE TABLE payments(reference TEXT PRIMARY KEY, invoice TEXT, amount INTEGER, evidence TEXT);
                    CREATE TABLE expenses(reference TEXT PRIMARY KEY, amount INTEGER, evidence TEXT);
                ''')

    @contextmanager
    def _db(self):
        private_file(self.path)
        db = sqlite3.connect(self.path, timeout=1)
        try:
            with db: yield db
        except sqlite3.IntegrityError:
            raise ValueError('Duplicate ledger reference.') from None
        finally: db.close()

    def _authorize(self, actor):
        if actor != self.owner: raise Denied('Ledger access denied.')

    @staticmethod
    def _capacity(db, table):
        # Table names are fixed internal constants, never request text.
        queries = {'deals': 'SELECT COUNT(*) FROM deals', 'invoices': 'SELECT COUNT(*) FROM invoices',
                   'payments': 'SELECT COUNT(*) FROM payments', 'expenses': 'SELECT COUNT(*) FROM expenses'}
        if db.execute(queries[table]).fetchone()[0] >= 10000: raise ValueError('Ledger capacity reached.')

    def opportunity(self, actor, title, estimated_revenue_paise=0):
        self._authorize(actor); knowledge_text(title, 512); nonnegative_int(estimated_revenue_paise)
        ident = uuid4().hex
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE'); self._capacity(db, 'deals')
            db.execute('INSERT INTO deals VALUES (?,?,?,?,?)', (ident, title, estimated_revenue_paise, 'found', ''))
        return ident

    def advance(self, actor, identifier, target, *, evidence_ref):
        self._authorize(actor); knowledge_text(evidence_ref, 256)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT state FROM deals WHERE id=?', (identifier,)).fetchone()
            if not row or row[0] == STAGES[-1] or target != STAGES[STAGES.index(row[0])+1]:
                raise ValueError('Invalid earnings lifecycle transition.')
            db.execute('UPDATE deals SET state=?,evidence=? WHERE id=?', (target, evidence_ref, identifier))

    def invoice(self, actor, deal, amount_paise):
        self._authorize(actor)
        if not nonnegative_int(amount_paise): raise ValueError('Positive invoice amount required.')
        ident = uuid4().hex
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE'); self._capacity(db, 'invoices')
            row = db.execute('SELECT state FROM deals WHERE id=?', (deal,)).fetchone()
            if not row or row[0] != 'project_completed': raise ValueError('Completed project required before invoicing.')
            db.execute('INSERT INTO invoices VALUES (?,?,?)', (ident, deal, amount_paise))
        return ident

    def payment(self, actor, invoice, amount_paise, *, reference, evidence_ref, confirmed=False):
        self._authorize(actor); knowledge_text(reference, 128); knowledge_text(evidence_ref, 256)
        if confirmed is not True or not nonnegative_int(amount_paise): raise ValueError('Owner-confirmed positive payment required.')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            self._capacity(db, 'payments')
            row = db.execute('SELECT amount FROM invoices WHERE id=?', (invoice,)).fetchone()
            paid = db.execute('SELECT COALESCE(SUM(amount),0) FROM payments WHERE invoice=?', (invoice,)).fetchone()[0]
            if not row or paid + amount_paise > row[0]: raise ValueError('Invalid invoice or excess payment.')
            db.execute('INSERT INTO payments VALUES (?,?,?,?)', (reference, invoice, amount_paise, evidence_ref))

    def expense(self, actor, amount_paise, *, reference, evidence_ref, confirmed=False):
        self._authorize(actor); knowledge_text(reference, 128); knowledge_text(evidence_ref, 256)
        if confirmed is not True or not nonnegative_int(amount_paise): raise ValueError('Owner-confirmed positive expense required.')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE'); self._capacity(db, 'expenses')
            db.execute('INSERT INTO expenses VALUES (?,?,?)', (reference, amount_paise, evidence_ref))

    def invoice_status(self, actor, identifier):
        self._authorize(actor)
        with self._db() as db:
            row = db.execute('SELECT amount FROM invoices WHERE id=?', (identifier,)).fetchone()
            if not row: raise KeyError('Invoice unavailable.')
            paid = db.execute('SELECT COALESCE(SUM(amount),0) FROM payments WHERE invoice=?', (identifier,)).fetchone()[0]
        return 'paid' if paid == row[0] else 'partial' if paid else 'unpaid'

    def report(self, actor):
        self._authorize(actor)
        with self._db() as db:
            states = [r[0] for r in db.execute('SELECT state FROM deals')]
            estimate = db.execute('SELECT COALESCE(SUM(estimate),0) FROM deals').fetchone()[0]
            paid = db.execute('SELECT COALESCE(SUM(amount),0) FROM payments').fetchone()[0]
            spent = db.execute('SELECT COALESCE(SUM(amount),0) FROM expenses').fetchone()[0]
            invoices = db.execute('SELECT COUNT(*),COALESCE(SUM(amount),0) FROM invoices').fetchone()
        return {'currency': 'INR', 'opportunities_found': len(states),
                'proposals_submitted': sum(STAGES.index(s) >= 1 for s in states),
                'clients_acquired': sum(STAGES.index(s) >= 2 for s in states),
                'projects_completed': states.count('project_completed'),
                'invoices': invoices[0], 'invoiced_paise': invoices[1],
                'estimated_revenue_paise': estimate, 'confirmed_payments_paise': paid,
                'confirmed_expenses_paise': spent, 'actual_profit_paise': paid-spent,
                'confirmation_origin': 'operator_recorded', 'bank_verified': False}
