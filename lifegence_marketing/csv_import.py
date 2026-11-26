# Copyright (c) 2026, Lifegence Corporation
# License: Apache-2.0. See license.txt

"""Reading a channel's CSV export of ad performance.

Columns are recognised from common English and Japanese headers (a profile can name the others). The encoding is
UTF-8 or Shift_JIS (cp932), the delimiter comma, tab or semicolon. Total rows and rows without a date are skipped.
"""

import csv
import datetime
import io
import re

from frappe import _

ALIASES = {
	"date": ["date", "day", "reporting starts", "日", "日付", "日別", "レポート開始日", "期間"],
	"campaign_id": ["campaign id", "キャンペーンid", "キャンペーン id"],
	"campaign_name": ["campaign", "campaign name", "キャンペーン", "キャンペーン名"],
	"ad_group_id": ["ad group id", "ad set id", "広告グループid", "広告セットid"],
	"ad_group_name": [
		"ad group",
		"ad group name",
		"ad set",
		"ad set name",
		"広告グループ",
		"広告グループ名",
		"広告セット",
		"広告セット名",
	],
	"ad_id": ["ad id", "広告id"],
	"ad_name": ["ad", "ad name", "広告", "広告名"],
	"placement": ["placement", "platform", "publisher platform", "プラットフォーム", "配置", "配信面"],
	"impressions": ["impressions", "impr.", "インプレッション", "インプレッション数", "表示回数"],
	"reach": ["reach", "リーチ", "リーチ数"],
	"clicks": ["clicks", "clicks (all)", "link clicks", "クリック", "クリック数", "クリック数(すべて)"],
	"cost": ["cost", "spend", "amount spent", "費用", "コスト", "消化金額", "ご利用金額", "広告費"],
	"conversions": ["conversions", "results", "conv.", "コンバージョン", "コンバージョン数", "結果"],
	"conversion_value": [
		"conversion value",
		"conv. value",
		"all conv. value",
		"purchase conversion value",
		"コンバージョン値",
		"コンバージョンの価値",
		"売上",
	],
	"currency": ["currency", "currency code", "通貨", "通貨コード"],
}
TOTALS = ("total", "合計", "総計", "--")
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日", "%m/%d/%Y", "%d/%m/%Y", "%Y%m%d")


def norm(header):
	"""'Amount spent (JPY)' -> 'amount spent'; full-width spaces and brackets are folded."""
	h = (
		(header or "")
		.replace("\ufeff", "")
		.replace("\uff08", "(")
		.replace("\uff09", ")")
		.replace("\u3000", " ")
	)
	h = re.sub(r"\((jpy|usd|eur|円|\$|¥)\)", "", h, flags=re.I)
	return re.sub(r"\s+", " ", h).strip().lower()


def decode(content, encoding="Auto"):
	if isinstance(content, str):
		return content
	if encoding and encoding != "Auto":
		return content.decode(encoding)
	for enc in ("utf-8-sig", "cp932"):
		try:
			return content.decode(enc)
		except UnicodeDecodeError:
			continue
	raise ValueError(_("The file is neither UTF-8 nor Shift_JIS"))


def number(value):
	v = (value or "").strip()
	for mark in (
		",",
		"\u00a5",
		"\uffe5",
		"$",
		"\u5186",
		"%",
		"\uff05",
	):  # comma, yen (half/full width), dollar, en, percent
		v = v.replace(mark, "")
	if v in ("", "-", "--", "—"):
		return 0
	try:
		return float(v)
	except ValueError:
		raise ValueError(_("Not a number: {0}").format(value)) from None


def parse_date(value, fmt=None):
	v = (value or "").strip()
	v = re.split(r"\s+[-~〜]\s+|\s*〜\s*", v)[0].strip()  # a period 'start - end' takes the start
	for f in [fmt] if fmt else DATE_FORMATS:
		try:
			return datetime.datetime.strptime(v, f).date()
		except TypeError, ValueError:
			continue
	raise ValueError(_("Not a date: {0}").format(value))


def column_map(headers, profile_columns=None):
	"""target -> column index."""
	by_norm = {norm(h): i for i, h in enumerate(headers)}
	mapping = {}
	for target, column in (profile_columns or {}).items():
		if norm(column) in by_norm:
			mapping[target] = by_norm[norm(column)]
	for target, names in ALIASES.items():
		if target in mapping:
			continue
		for name in names:
			if name in by_norm:
				mapping[target] = by_norm[name]
				break
	return mapping


def read(content, encoding="Auto", skip_rows=0, date_format=None, profile_columns=None):
	"""Rows as dicts, and messages for the skipped lines."""
	text = decode(content, encoding)
	lines = text.splitlines()[int(skip_rows or 0) :]
	sample = "\n".join(lines[:5])
	try:
		dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
	except csv.Error:
		dialect = csv.excel
	reader = csv.reader(io.StringIO("\n".join(lines)), dialect)
	headers = next(reader, [])
	mapping = column_map(headers, profile_columns)
	if "date" not in mapping:
		raise ValueError(_("No date column was found. Headers: {0}").format(", ".join(headers)))
	if not ({"cost", "impressions", "clicks"} & set(mapping)):
		raise ValueError(
			_("No cost, impression or click column was found. Headers: {0}").format(", ".join(headers))
		)
	rows, messages = [], []
	for line_no, cells in enumerate(reader, start=int(skip_rows or 0) + 2):
		if not any(c.strip() for c in cells):
			continue
		get = lambda t: cells[mapping[t]] if t in mapping and mapping[t] < len(cells) else ""  # noqa: E731
		first = (cells[0] if cells else "").strip().lower()
		if first.startswith(TOTALS) or not get("date").strip():
			continue
		try:
			row = {"date": parse_date(get("date"), date_format)}
			for t in (
				"campaign_id",
				"campaign_name",
				"ad_group_id",
				"ad_group_name",
				"ad_id",
				"ad_name",
				"placement",
				"currency",
			):
				row[t] = get(t).strip()
			for t in ("impressions", "reach", "clicks", "cost", "conversions", "conversion_value"):
				row[t] = number(get(t))
			rows.append(row)
		except ValueError as e:
			messages.append(_("Line {0}: {1}").format(line_no, str(e)))
	return rows, messages
