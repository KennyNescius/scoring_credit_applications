extra = {
    "uw.stat.total": {"ru": "Всего", "uz": "Jami"},
    "uw.stat.appr": {"ru": "Одобрено", "uz": "Ma'qullangan"},
    "uw.stat.rej": {"ru": "Отказано", "uz": "Rad etilgan"},
    "uw.stat.avg": {"ru": "Средний скор", "uz": "O'rtacha skor"},
    "uw.lbl.data": {"ru": "Данные:", "uz": "Ma'lumotlar:"},
    "uw.filter.all": {"ru": "Все", "uz": "Barchasi"},
    "uw.th.id": {"ru": "ID заявки", "uz": "Ariza ID"},
    "uw.th.name": {"ru": "Имя", "uz": "Ism"},
    "uw.th.score": {"ru": "Скор", "uz": "Skor"},
    "uw.th.pd": {"ru": "PD", "uz": "PD"},
    "uw.th.fact": {"ru": "Факт", "uz": "Fakt"},
    "uw.th.inc": {"ru": "Доход", "uz": "Daromad"},
    "uw.th.dti": {"ru": "DTI", "uz": "DTI"},
    "uw.badge.appr": {"ru": "Одобрено", "uz": "Ma'qullangan"},
    "uw.badge.rej": {"ru": "Отказ", "uz": "Rad etildi"},
    "uw.btn.detail": {"ru": "Детали →", "uz": "Batafsil →"},
    "uw.btn.next": {"ru": "Далее →", "uz": "Keyingisi →"}
}

with open("translations.py", "r", encoding="utf-8") as f:
    t_content = f.read()

extra_str = ""
for k, v in extra.items():
    extra_str += f'    "{k}": {v},\n'

t_content = t_content.replace('"pts": {"ru": "баллов", "uz": "ball"},', f'"pts": {{"ru": "баллов", "uz": "ball"}},\n{extra_str}')
with open("translations.py", "w", encoding="utf-8") as f:
    f.write(t_content)

html = """{% extends "base.html" %}
{% block title %}{{ t("uw.title") }}{% endblock %}

{% block content %}
<div class="page-header">
    <h1>{{ t("uw.title") }}</h1>
    <p class="subtitle">{{ t('uw.all_apps') }}</p>
</div>

<div class="stats-grid stats-small">
    <div class="stat-card stat-blue" id="uw-stat-total">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">{{ t('uw.stat.total') }}</div>
    </div>
    <div class="stat-card stat-green" id="uw-stat-approved">
        <div class="stat-value">
            {{ stats.approved }} 
            <span style="font-size: 0.6em; opacity: 0.8; font-weight: 500;">({{ stats.approved_pct }})</span>
        </div>
        <div class="stat-label">{{ t('uw.stat.appr') }}</div>
    </div>
    <div class="stat-card stat-red" id="uw-stat-rejected">
        <div class="stat-value">
            {{ stats.rejected }} 
            <span style="font-size: 0.6em; opacity: 0.8; font-weight: 500;">({{ stats.rejected_pct }})</span>
        </div>
        <div class="stat-label">{{ t('uw.stat.rej') }}</div>
    </div>
    <div class="stat-card stat-orange" id="uw-stat-avg">
        <div class="stat-value">
            {{ stats.avg_score }}
            <span style="font-size: 0.6em; opacity: 0.8; font-weight: 500;">/ 1000</span>
        </div>
        <div class="stat-label">{{ t('uw.stat.avg') }} ({{ t('index.cards.threshold') }} {{ threshold }})</div>
    </div>
</div>

<div class="filters-bar" id="filters">
    <div class="filter-group">
        <label>{{ t('uw.lbl.data') }}</label>
        <a href="{{ url_for('underwriter', filter='all', decision=filter_decision) }}" class="filter-btn {% if filter_type == 'all' %}active{% endif %}">{{ t('uw.filter.all') }}</a>
        <a href="{{ url_for('underwriter', filter='train', decision=filter_decision) }}" class="filter-btn {% if filter_type == 'train' %}active{% endif %}">Train</a>
        <a href="{{ url_for('underwriter', filter='test', decision=filter_decision) }}" class="filter-btn {% if filter_type == 'test' %}active{% endif %}">Test</a>
    </div>
    <div class="filter-group">
        <label>{{ t('uw.table.decision') }}</label>
        <a href="{{ url_for('underwriter', filter=filter_type, decision='all') }}" class="filter-btn {% if filter_decision == 'all' %}active{% endif %}">{{ t('uw.filter.all') }}</a>
        <a href="{{ url_for('underwriter', filter=filter_type, decision='toladi') }}" class="filter-btn {% if filter_decision == 'toladi' %}active{% endif %}">{{ t('uw.stat.appr') }}</a>
        <a href="{{ url_for('underwriter', filter=filter_type, decision='defolt') }}" class="filter-btn {% if filter_decision == 'defolt' %}active{% endif %}">{{ t('uw.badge.rej') }}</a>
    </div>
</div>

<div class="table-container" id="applications-table">
    <table class="data-table">
        <thead>
            <tr>
                <th>{{ t('uw.th.id') }}</th>
                <th>{{ t('uw.th.name') }}</th>
                <th>{{ t('uw.th.score') }}</th>
                <th>{{ t('uw.th.pd') }}</th>
                <th>{{ t("uw.table.decision") }}</th>
                <th>{{ t('uw.th.fact') }}</th>
                <th>{{ t("uw.table.amount") }}</th>
                <th>{{ t('f.purpose') }}</th>
                <th>{{ t('uw.th.inc') }}</th>
                <th>{{ t('uw.th.dti') }}</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            {% for app in applications %}
            <tr class="{{ 'row-danger' if app.decision == 'defolt' else 'row-success' }}" id="row-{{ app.application_id }}">
                <td class="mono">{{ app.application_id }}</td>
                <td>{{ app.ism }}</td>
                <td>
                    <span class="score-badge {{ 'score-good' if app.score >= 500 else ('score-medium' if app.score >= threshold else 'score-bad') }}">
                        {{ app.score }}
                    </span>
                </td>
                <td>{{ (app.pd * 100)|round(1) }}%</td>
                <td>
                    <span class="decision-badge {{ app.decision }}">
                        {{ t('uw.badge.appr') if app.decision == 'toladi' else t('uw.badge.rej') }}
                    </span>
                </td>
                <td>
                    {% if app.actual != '—' and app.actual is not none %}
                    <span class="actual-badge {{ app.actual }}">{{ app.actual }}</span>
                    {% else %}
                    <span class="actual-badge unknown">—</span>
                    {% endif %}
                </td>
                <td class="num">{{ app.amount }}</td>
                <td>{{ app.purpose }}</td>
                <td class="num">{{ app.income }}</td>
                <td>
                    <span class="{{ 'text-danger' if app.dti > 0.5 else ('text-warning' if app.dti > 0.3 else 'text-success') }}">
                        {{ app.dti }}
                    </span>
                </td>
                <td>
                    <a href="{{ url_for('application_detail', app_id=app.application_id) }}" class="btn btn-sm">{{ t('uw.btn.detail') }}</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

{% if total_pages > 1 %}
<div class="pagination" id="pagination">
    {% if page > 1 %}
    <a href="{{ url_for('underwriter', page=page-1, filter=filter_type, decision=filter_decision) }}" class="page-btn">{{ t('btn.back') }}</a>
    {% endif %}

    {% for p in range(1, total_pages + 1) %}
        {% if p == page %}
        <span class="page-btn active">{{ p }}</span>
        {% elif p <= 3 or p >= total_pages - 2 or (p >= page - 2 and p <= page + 2) %}
        <a href="{{ url_for('underwriter', page=p, filter=filter_type, decision=filter_decision) }}" class="page-btn">{{ p }}</a>
        {% elif p == 4 or p == total_pages - 3 %}
        <span class="page-dots">...</span>
        {% endif %}
    {% endfor %}

    {% if page < total_pages %}
    <a href="{{ url_for('underwriter', page=page+1, filter=filter_type, decision=filter_decision) }}" class="page-btn">{{ t('uw.btn.next') }}</a>
    {% endif %}
</div>
{% endif %}
{% endblock %}
"""
with open("templates/underwriter.html", "w", encoding="utf-8") as f:
    f.write(html)
