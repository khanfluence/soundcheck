from typing import Any, Optional

DEBUG: Any

class TinyTagException(LookupError): ...

class TinyTag:
    filesize: Optional[int]
    album: Optional[str]
    albumartist: Optional[str]
    artist: Optional[str]
    audio_offset: Optional[int]
    bitrate: Optional[int]
    channels: Optional[int]
    comment: Optional[str]
    composer: Optional[str]
    disc: Optional[str]
    disc_total: Optional[str]
    duration: Optional[float]
    extra: dict
    genre: Optional[str]
    samplerate: Optional[int]
    title: Optional[str]
    track: Optional[str]
    track_total: Optional[str]
    year: Optional[str]
    def __init__(self, filehandler, filesize, ignore_errors: bool = ...) -> None: ...
    def as_dict(self): ...
    @classmethod
    def is_supported(cls, filename): ...
    def get_image(self) -> Optional[bytes]: ...
    @classmethod
    def get_parser_class(cls, filename, filehandle): ...
    @classmethod
    def get(cls, filename, tags: bool = ..., duration: bool = ..., image: bool = ..., ignore_errors: bool = ..., encoding: Any | None = ...): ...
    def load(self, tags, duration, image: bool = ...) -> None: ...
    def update(self, other) -> None: ...

class MP4(TinyTag):
    class Parser:
        ATOM_DECODER_BY_TYPE: Any
        @classmethod
        def make_data_atom_parser(cls, fieldname): ...
        @classmethod
        def make_number_parser(cls, fieldname1, fieldname2): ...
        @classmethod
        def parse_id3v1_genre(cls, data_atom): ...
        @classmethod
        def parse_audio_sample_entry(cls, data): ...
        @classmethod
        def parse_mvhd(cls, data): ...
        @classmethod
        def debug_atom(cls, data): ...
    META_DATA_TREE: Any
    AUDIO_DATA_TREE: Any
    IMAGE_DATA_TREE: Any
    VERSIONED_ATOMS: Any
    FLAGGED_ATOMS: Any

class ID3(TinyTag):
    FRAME_ID_TO_FIELD: Any
    IMAGE_FRAME_IDS: Any
    PARSABLE_FRAME_IDS: Any
    ID3V1_GENRES: Any
    def __init__(self, filehandler, filesize, *args, **kwargs) -> None: ...
    @classmethod
    def set_estimation_precision(cls, estimation_in_seconds) -> None: ...
    samplerates: Any
    v1l1: Any
    v1l2: Any
    v1l3: Any
    v2l1: Any
    v2l2: Any
    v2l3: Any
    bitrate_by_version_by_layer: Any
    samples_per_frame: int
    channels_per_channel_mode: Any
    @staticmethod
    def index_utf16(s, search): ...

class Ogg(TinyTag):
    def __init__(self, filehandler, filesize, *args, **kwargs) -> None: ...

class Wave(TinyTag):
    riff_mapping: Any
    def __init__(self, filehandler, filesize, *args, **kwargs) -> None: ...

class Flac(TinyTag):
    METADATA_STREAMINFO: int
    METADATA_PADDING: int
    METADATA_APPLICATION: int
    METADATA_SEEKTABLE: int
    METADATA_VORBIS_COMMENT: int
    METADATA_CUESHEET: int
    METADATA_PICTURE: int
    def load(self, tags, duration, image: bool = ...) -> None: ...

class Wma(TinyTag):
    ASF_CONTENT_DESCRIPTION_OBJECT: bytes
    ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT: bytes
    STREAM_BITRATE_PROPERTIES_OBJECT: bytes
    ASF_FILE_PROPERTY_OBJECT: bytes
    ASF_STREAM_PROPERTIES_OBJECT: bytes
    STREAM_TYPE_ASF_AUDIO_MEDIA: bytes
    def __init__(self, filehandler, filesize, *args, **kwargs) -> None: ...
    def read_blocks(self, fh, blocks): ...

class Aiff(ID3):
    def __init__(self, filehandler, filesize, *args, **kwargs) -> None: ...
