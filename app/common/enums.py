"""Shared enums used across multiple business domains."""

from enum import Enum as PyEnum


class SubmissionMethod(str, PyEnum):
    ONLINE = "online"  # שידור ישיר (מייצגים)
    MANUAL = "manual"  # הגשה פיזית לפקיד השומה
    REPRESENTATIVE = "representative"  # דרך מערכת המייצגים (שע"מ)


__all__ = ["SubmissionMethod"]
