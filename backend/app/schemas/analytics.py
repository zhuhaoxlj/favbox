"""
Analytics Schemas
"""
from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    total_bookmarks: int
    total_domains: int
    total_tags: int
    total_folders: int
    pinned_count: int
    dead_links_count: int  # HTTP status 4xx/5xx


class DomainStat(BaseModel):
    domain: str
    count: int


class TagStat(BaseModel):
    tag: str
    count: int


class TimelineStat(BaseModel):
    date: str  # ISO date string
    count: int


class DuplicateGroup(BaseModel):
    url: str
    bookmarks: list[dict]
    count: int
