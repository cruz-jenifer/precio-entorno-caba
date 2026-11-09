from collections import defaultdict
from statistics import median


def matches(item, budget, min_area, rooms, currency='USD'):
    """Un aviso encaja si está en la moneda de la búsqueda y cumple presupuesto, superficie y ambientes."""
    return ((item.get('currency') or 'USD') == currency and item['price'] <= budget
            and item['covered_area'] >= min_area and item['rooms'] == rooms)


def compare_neighborhoods(listings, budget, min_area, rooms, currency='USD'):
    """Coincidencias por barrio en la moneda de la búsqueda; no convierte monedas."""
    by_neighborhood = defaultdict(list)
    for item in listings:
        if (item.get('currency') or 'USD') == currency:
            by_neighborhood[item['neighborhood']].append(item)

    comparison = []
    for neighborhood, items in by_neighborhood.items():
        found = [item for item in items if matches(item, budget, min_area, rooms, currency)]
        prices = [item['price'] for item in found]
        comparison.append({
            'Barrio': neighborhood,
            'Coincidencias': len(found),
            f'Precio mediano de coincidencias ({currency})': int(median(prices)) if prices else None,
        })
    return sorted(comparison, key=lambda row: (-row['Coincidencias'], row['Barrio']))
