"""
bibliometria — Análisis de algoritmos en el contexto de la bibliometría.

Paquete principal del proyecto final de Análisis de Algoritmos (2026-2),
Universidad del Quindío. Contiene:

- ``extraction``       : extracción de título, autores y abstract desde los PDF.
- ``preprocessing``    : normalización, tokenización, stopwords y stemming de Porter.
- ``similarity``       : Requerimiento 1 (4 algoritmos clásicos + 2 modelos de IA).
- ``clustering``       : Requerimiento 2 (agrupamiento jerárquico y dendrogramas).
- ``string_matching``  : Requerimiento 3 (KMP, Boyer-Moore y Rabin-Karp).
- ``api``              : Requerimiento 4 (servicio web FastAPI que expone todo lo anterior).

Todos los algoritmos solicitados están implementados de forma explícita con
estructuras básicas del lenguaje (listas, diccionarios, ciclos), sin funciones
de alto nivel que los resuelvan directamente.
"""

__version__ = "1.0.0"

AUTHORS = [
    "Mariana Muñoz Rodriguez",
    "Andres Felipe Correa Valencia",
    "Ivan Alexander Cardona",
    "Milton Cesar Gomez Roso",
]
