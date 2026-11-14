"""Explicit customer-field exports; never serialize account internals."""

import csv
import io
import json

from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .views import AdminCustomerListView

FIELDS = (
    'id', 'username', 'first_name', 'last_name', 'email', 'phone', 'city',
    'country', 'date_joined', 'is_active', 'order_count', 'total_spent',
)


def spreadsheet_cell(value):
    text = '' if value is None else str(value)
    # Quoting alone does not stop Excel from evaluating exported formulas.
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text


def export_rows(queryset):
    for row in queryset.values(*FIELDS).iterator(chunk_size=500):
        row['date_joined'] = row['date_joined'].isoformat()
        row['total_spent'] = format(row['total_spent'] or 0, '.2f')
        yield row


def csv_chunks(rows):
    yield '\ufeff'  # Excel-friendly UTF-8, including Bengali customer names.
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(FIELDS)
    yield buffer.getvalue()
    for row in rows:
        buffer.seek(0)
        buffer.truncate()
        writer.writerow([spreadsheet_cell(row[field]) for field in FIELDS])
        yield buffer.getvalue()


def json_chunks(rows):
    yield '['
    for index, row in enumerate(rows):
        yield (',' if index else '') + json.dumps(row, ensure_ascii=False)
    yield ']'


class AdminCustomerExportView(AdminCustomerListView):
    """Export all search matches, independently of the visible list page."""

    def get(self, request, *args, **kwargs):
        file_type = request.query_params.get('file_type', 'csv')
        if file_type not in {'csv', 'json'}:
            raise ValidationError({'file_type': 'Choose csv or json.'})
        queryset = self.get_queryset().order_by('-date_joined', '-pk')
        rows = export_rows(queryset)
        content = csv_chunks(rows) if file_type == 'csv' else json_chunks(rows)
        content_type = 'text/csv' if file_type == 'csv' else 'application/json'
        response = StreamingHttpResponse(content, content_type=content_type + '; charset=utf-8')
        stamp = timezone.now().strftime('%Y-%m-%d')
        response['Content-Disposition'] = f'attachment; filename="fabrything-customers-{stamp}.{file_type}"'
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
