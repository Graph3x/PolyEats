from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Address(_message.Message):
    __slots__ = ("street", "building_number", "city", "postal_code")
    STREET_FIELD_NUMBER: _ClassVar[int]
    BUILDING_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    POSTAL_CODE_FIELD_NUMBER: _ClassVar[int]
    street: str
    building_number: str
    city: str
    postal_code: str
    def __init__(self, street: _Optional[str] = ..., building_number: _Optional[str] = ..., city: _Optional[str] = ..., postal_code: _Optional[str] = ...) -> None: ...

class Coordinates(_message.Message):
    __slots__ = ("lat", "lon")
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ...) -> None: ...

class GeocodeRequest(_message.Message):
    __slots__ = ("address",)
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    address: Address
    def __init__(self, address: _Optional[_Union[Address, _Mapping]] = ...) -> None: ...

class GeocodeResponse(_message.Message):
    __slots__ = ("coordinates",)
    COORDINATES_FIELD_NUMBER: _ClassVar[int]
    coordinates: Coordinates
    def __init__(self, coordinates: _Optional[_Union[Coordinates, _Mapping]] = ...) -> None: ...

class ReverseGeocodeRequest(_message.Message):
    __slots__ = ("coordinates",)
    COORDINATES_FIELD_NUMBER: _ClassVar[int]
    coordinates: Coordinates
    def __init__(self, coordinates: _Optional[_Union[Coordinates, _Mapping]] = ...) -> None: ...

class ReverseGeocodeResponse(_message.Message):
    __slots__ = ("address",)
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    address: Address
    def __init__(self, address: _Optional[_Union[Address, _Mapping]] = ...) -> None: ...
