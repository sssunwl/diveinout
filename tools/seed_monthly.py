"""Conservative calendar draft from existing creature-to-spot associations."""
def seed_monthly(spot, creatures):
    spot['monthly'] = {str(m): [{'c': c['id'], 'p': 'low'} for c in creatures if spot['id'] in c.get('spots', [])] if m in spot['months'] else [] for m in range(1, 13)}
    spot.update(monthlyNote='月份待查證', monthlySeed=True)
    return spot
