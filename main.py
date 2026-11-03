"""
Menú principal por consola del proyecto.

Uso:  python main.py
"""

from __future__ import annotations

import sys
import warnings

warnings.filterwarnings("ignore")


def _ask_ids(prompt: str) -> list[int]:
    raw = input(prompt).strip()
    return [int(x) for x in raw.replace(";", ",").split(",") if x.strip()]


def opcion_extraer() -> None:
    from bibliometria.extraction.build_corpus import build_corpus

    arts = build_corpus()
    print(f"\nCorpus regenerado: {len(arts)} artículos en data/processed/corpus.json")


def opcion_listar() -> None:
    from bibliometria.corpus import load_corpus

    for a in load_corpus():
        autores = ", ".join(a.authors[:3]) + (" et al." if len(a.authors) > 3 else "")
        print(f"{a.id:>2}. [{a.year}] {a.title}\n     {autores}")


def opcion_similitud() -> None:
    from bibliometria.similarity.service import get_engine

    engine = get_engine()
    ids = _ask_ids("IDs de los artículos a comparar (ej: 11,16,17): ")
    gran = input("Levenshtein por (p)alabras o (c)aracteres [p]: ").strip().lower()
    result = engine.compare(ids, granularity="chars" if gran == "c" else "words")
    algs = [a["key"] for a in result["algorithms"]]
    labels = {a["key"]: a["label"] for a in result["algorithms"]}
    for pair in result["pairs"]:
        print(f"\nArtículo {pair['a']} vs artículo {pair['b']}")
        for alg in algs:
            s = pair["scores"][alg]
            print(f"  {labels[alg]:<26} {s['value']:.4f}   ({s['ms']:.2f} ms)")


def opcion_clustering() -> None:
    from bibliometria.clustering.service import get_clustering_engine

    rep = input("Representación (t)f-idf o (s)bert [t]: ").strip().lower()
    representation = "sbert" if rep == "s" else "tfidf"
    engine = get_clustering_engine()
    result = engine.run(representation)
    print(f"\nRepresentación: {result['representation_label']}")
    print(f"{'Método':<10} {'CPCC':>7} {'Silueta media':>14} {'k*':>4} {'Silueta(k*)':>12}")
    for m, r in result["methods"].items():
        print(f"{m:<10} {r['cophenetic_correlation']:>7.3f} {r['silhouette_mean']:>14.3f} {r['best_k']:>4} {r['best_silhouette']:>12.3f}")
    print(f"\nMétodo más coherente (entre los 3 exigidos): {result['best_required_method']}")
    for path in engine.export_outputs(representation):
        print("  generado:", path)


def opcion_busqueda() -> None:
    from bibliometria.string_matching.service import search_corpus

    pattern = input("Patrón a buscar: ")
    campos = input("Campos (abstract,title,authors,keywords) [abstract]: ").strip() or "abstract"
    result = search_corpus(pattern, fields=[c.strip() for c in campos.split(",")])
    print(f"\n{result['total_occurrences']} ocurrencias en {result['documents_with_matches']} artículos")
    for r in result["results"]:
        print(f"  {r['code']} ({r['field_label']}): {r['count']} — {r['title'][:70]}")
        for occ in r["occurrences"][:2]:
            print(f"      …{occ['before'][-40:]}[{occ['match']}]{occ['after'][:40]}…")
    print("\nAlgoritmo        comparaciones   preproc (µs)   búsqueda (µs)")
    for alg, t in result["totals"].items():
        print(f"  {alg:<14} {t['comparisons']:>12}   {t['preprocessing_ns'] / 1000:>11.1f}   {t['search_ns'] / 1000:>12.1f}")
    print("Resultados consistentes entre algoritmos:", result["consistent"])


def opcion_benchmark() -> None:
    from bibliometria.string_matching.benchmark import run_benchmark, save_benchmark

    print("Ejecutando benchmark (puede tardar ~30 s)...")
    res = run_benchmark()
    save_benchmark(res)
    print(f"Listo en {res['meta']['seconds']} s -> data/processed/benchmark_string_matching.json")


def opcion_servidor() -> None:
    import uvicorn

    print("Servidor en http://localhost:8000  (documentación de la API en /docs)")
    uvicorn.run("bibliometria.api.main:app", host="0.0.0.0", port=8000)


OPCIONES = {
    "1": ("Extraer/actualizar el corpus desde los PDF", opcion_extraer),
    "2": ("Listar artículos del corpus", opcion_listar),
    "3": ("Requerimiento 1 — Comparar artículos (similitud textual)", opcion_similitud),
    "4": ("Requerimiento 2 — Agrupamiento jerárquico y dendrogramas", opcion_clustering),
    "5": ("Requerimiento 3 — Buscar un patrón (KMP, Boyer-Moore, Rabin-Karp)", opcion_busqueda),
    "6": ("Requerimiento 3 — Benchmark de los algoritmos de búsqueda", opcion_benchmark),
    "7": ("Requerimiento 4 — Iniciar la aplicación web (API + interfaz)", opcion_servidor),
}


def menu() -> None:
    while True:
        print("\n===== ANÁLISIS DE ALGORITMOS EN BIBLIOMETRÍA =====")
        for key, (label, _) in OPCIONES.items():
            print(f"{key}. {label}")
        print("0. Salir")
        choice = input("Seleccione una opción: ").strip()
        if choice == "0":
            print("Hasta luego.")
            return
        option = OPCIONES.get(choice)
        if option is None:
            print("Opción no válida.")
            continue
        try:
            option[1]()
        except (ValueError, KeyError) as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    try:
        menu()
    except (KeyboardInterrupt, EOFError):
        sys.exit(0)
