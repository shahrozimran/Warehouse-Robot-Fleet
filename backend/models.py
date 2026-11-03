from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

PolicyId=Literal['fifo','nearest','auction']
ScenarioId=Literal['standard','peak','blocked','low_battery']
class RunRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    policy:PolicyId='auction'
    scenario:ScenarioId='standard'
    fleet_size:int=Field(6,ge=2,le=10)
    order_count:int=Field(24,ge=4,le=80)
    max_ticks:int=Field(500,ge=100,le=1000)
    seed:int=Field(42,ge=0,le=2147483647)
class ComparisonRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    scenario:ScenarioId='standard'
    fleet_size:int=Field(6,ge=2,le=10)
    order_count:int=Field(24,ge=4,le=80)
    max_ticks:int=Field(500,ge=100,le=1000)
    seed:int=Field(42,ge=0,le=2147483647)
class SavedComparison(BaseModel):
    model_config=ConfigDict(extra='forbid')
    run_ids:list[str]=Field(min_length=2,max_length=30)
