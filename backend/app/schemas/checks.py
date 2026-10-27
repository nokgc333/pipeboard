"""検査結果のスキーマ。入力は、ツール間で共通のレポート形式(unibridge の docs/schema と同じ)。"""

from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

TOOL_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,29}$"
MAX_FINDINGS = 2000


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: str = Field(min_length=1, max_length=100)
    severity: Literal["error", "warning", "info"]
    target: str = Field(max_length=500)
    message: str = Field(max_length=2000)


class CheckReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"]
    tool: str = Field(pattern=TOOL_PATTERN)
    generated_at: datetime.datetime
    subject: str = Field(max_length=255)
    has_errors: StrictBool
    findings: list[Finding] = Field(max_length=MAX_FINDINGS)


class CheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_type: Literal["shot", "asset"]
    item_id: int
    tool: str
    subject: str
    passed: bool
    error_count: int
    warning_count: int
    created_at: datetime.datetime
