from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)

class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    expires: Mapped[int] = mapped_column(Integer)

class Workspace(Base):
    __tablename__ = 'workspaces'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    data: Mapped[dict] = mapped_column(JSON)

Money = Annotated[int, Field(strict=True, ge=0, le=100_000_000_000)]
Category = Literal['Income', 'Food', 'Housing', 'Transport', 'Subscriptions', 'Fees', 'Bills', 'Shopping', 'Health', 'Education', 'Other', 'Uncategorized']

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Credentials(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        value = value.strip().lower()
        import re
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address')
        return value

class Signup(Credentials):
    name: str = Field(min_length=1, max_length=80)
    @field_validator('name')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('Name is required')
        return value.strip()

class Transaction(StrictModel):
    id: str = Field(min_length=1, max_length=400)
    date: date
    merchant: str = Field(min_length=1, max_length=200)
    amount: Money = Field(gt=0)
    direction: Literal['credit', 'debit']
    category: Category
    bank: str = Field(max_length=100)
    @field_validator('merchant')
    @classmethod
    def merchant_name(cls, value):
        if not value.strip(): raise ValueError('Merchant is required')
        return value.strip()

class Goal(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=60)
    target: Money = Field(gt=0)
    saved: Money
    deadline: date
    priority: Literal['High', 'Normal']
    @model_validator(mode='after')
    def savings_limit(self):
        if self.saved > self.target: raise ValueError('Savings cannot exceed goal target')
        return self

class Decision(StrictModel):
    status: Literal['accepted', 'rejected']
    amount: Money

class AlertState(StrictModel):
    read: bool = False
    dismissed: bool = False

class ImportLog(StrictModel):
    id: str = Field(max_length=100)
    label: str = Field(max_length=100)
    count: int = Field(ge=0, le=5000)
    duplicates: int = Field(ge=0, le=5000)
    at: str = Field(max_length=60)

class Bill(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    amount: Money = Field(gt=0)
    dueDate: date

class ScheduleInput(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    amount: Money = Field(gt=0)
    category: Category
    direction: Literal['debit', 'credit'] = 'debit'
    frequency: Literal['weekly', 'monthly', 'yearly', 'custom'] = 'monthly'
    interval: int = Field(default=1, ge=1, le=365)
    unit: Literal['days', 'weeks', 'months', 'years'] = 'months'
    startDate: date
    expectedDate: date
    endDate: date | None = None
    variable: bool = False
    @model_validator(mode='after')
    def dates(self):
        self.name = self.name.strip()
        if not self.name: raise ValueError('Name is required')
        if self.expectedDate < self.startDate: raise ValueError('First payment must be on or after the starting date')
        if self.endDate and self.endDate < self.expectedDate: raise ValueError('Ending date must include the first payment')
        if any(d and not 2000 <= d.year <= 2100 for d in [self.startDate, self.expectedDate, self.endDate]): raise ValueError('Use dates between 2000 and 2100')
        return self

class Schedule(ScheduleInput):
    id: str = Field(min_length=1, max_length=100)
    active: bool = True

class Occurrence(StrictModel):
    status: Literal['paid', 'skipped', 'postponed']
    transactionId: str | None = None
    postponedTo: date | None = None

class PatternDecision(StrictModel):
    status: Literal['accepted', 'declined', 'later']
    fingerprint: str
    remindOn: date | None = None

class FinancialState(StrictModel):
    asOf: date
    nextPayday: date
    transactions: list[Transaction] = Field(default_factory=list, max_length=5000)
    balance: Money = 0
    reserve: Money = 0
    salary: Money = 0
    bills: list[Bill] = Field(default_factory=list, max_length=100)
    consent: bool = False
    connections: list[str] = Field(default_factory=list, max_length=3)
    imports: list[ImportLog] = Field(default_factory=list, max_length=200)
    decisions: dict[str, Decision] = Field(default_factory=dict, max_length=100)
    alerts: dict[str, AlertState] = Field(default_factory=dict, max_length=300)
    goals: list[Goal] = Field(default_factory=list, max_length=50)
    theme: Literal['light', 'dark'] = 'light'
    schedules: list[Schedule] = Field(default_factory=list, max_length=100)
    occurrences: dict[str, Occurrence] = Field(default_factory=dict, max_length=10000)
    patternDecisions: dict[str, PatternDecision] = Field(default_factory=dict, max_length=500)
    @model_validator(mode='after')
    def consistency(self):
        if not 1 <= (self.nextPayday - self.asOf).days <= 90: raise ValueError('Next payday must be 1–90 days after the balance date')
        if any(t.date > self.asOf for t in self.transactions): raise ValueError('Transactions cannot be after the balance date')
        for items in [self.transactions, self.goals, self.bills, self.schedules]:
            if len({x.id for x in items}) != len(items): raise ValueError('Duplicate record IDs')
        linked = [event.transactionId for event in self.occurrences.values() if event.status == 'paid']
        if len(set(linked)) != len(linked) or any(identifier not in {t.id for t in self.transactions} for identifier in linked):
            raise ValueError('Each paid occurrence must link to one distinct recorded transaction')
        return self

class WorkspaceUpdate(StrictModel):
    version: int = Field(ge=1)
    state: FinancialState
    confirmed: bool = False

class Scenario(StrictModel):
    foodReduction: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    shopping: float = Field(default=0, ge=0, le=1_000_000, allow_inf_nan=False)
    purchase: float = Field(default=0, ge=0, le=1_000_000, allow_inf_nan=False)
    salaryDelay: int = Field(default=0, ge=0, le=60)
    emergency: float = Field(default=0, ge=0, le=1_000_000, allow_inf_nan=False)
    savings: float = Field(default=0, ge=0, le=1_000_000, allow_inf_nan=False)
    goalChange: float = Field(default=0, ge=0, le=1_000_000, allow_inf_nan=False)

class CategoryUpdate(StrictModel):
    category: Category
    version: int = Field(ge=1)

class Confirmed(StrictModel):
    confirmed: Literal[True]

class NewSchedule(StrictModel):
    version: int = Field(ge=1)
    confirmed: Literal[True]
    schedule: ScheduleInput

class ManualTransaction(StrictModel):
    version: int = Field(ge=1)
    transaction: Transaction
    schedule: ScheduleInput | None = None
    confirmed: bool = False

class ScheduleStatus(StrictModel):
    version: int = Field(ge=1)
    active: bool

class OccurrenceAction(StrictModel):
    version: int = Field(ge=1)
    status: Literal['paid', 'skipped', 'postponed', 'expected']
    confirmed: Literal[True]
    paymentDate: date | None = None
    amount: Money | None = Field(default=None, gt=0)
    postponedTo: date | None = None
    transactionId: str | None = None

class PatternAction(StrictModel):
    version: int = Field(ge=1)
    status: Literal['accepted', 'declined', 'later']
    confirmed: bool = False
