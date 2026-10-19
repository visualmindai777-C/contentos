from enum import StrEnum


class ContentStatus(StrEnum):
    IDEA = "idea"
    GUION = "guion"
    GENERADO = "generado"
    REVISADO = "revisado"
    APROBADO = "aprobado"
    PUBLICADO = "publicado"
    RECHAZADO = "rechazado"


class Platform(StrEnum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    X = "x"
