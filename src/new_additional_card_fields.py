"""
Add-on for Anki 2.1: Additional Card Fields for the reviewer

Copyright: (c) 2018- ijgnd
           (c) 2017 https://www.reddit.com/user/Dayjaby/
           (c) 2012- HSSM (Advanced Browser)
           (c) 2016 Dmitry Mikheev, http://finpapa.ucoz.net/
           (c) Damien Elmes <anki@ichi2.net>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.


This addon is a modification of "Additional Card Fields",
https://ankiweb.net/shared/info/441235634

"Additional Card Fields" also contains code from the add-on
"_Young_Mature_Card_Fields" which from
  https://ankiweb.net/shared/info/1751807495
  https://github.com/ankitest/anki-musthave-addons-by-ankitest

Updated for Anki 2.1.20. The template syntax has changed from

{{info::LastReview}}

to

{{info-LastReview:}}

The latter syntax will not display errors on Anki 2.1.20 or
AnkiMobile 2.0.56.
"""

import time
from typing import Any, Dict

from anki import hooks
from anki.stats import CardStats
from anki.template import TemplateRenderContext
from anki.utils import isWin, stripHTML
from aqt import mw
from aqt.addons import current_point_version

from .user_files.additional_user_fields import additional_user_fields

def gc(arg, fail=False):
    conf = mw.addonManager.getConfig(__name__)
    if conf:
        return conf.get(arg, fail)
    return fail


# from Advanced Browser - overdue_days
# https://github.com/hssm/advanced-browser/blob/master/advancedbrowser/advancedbrowser/custom_fields.py#L225
def valueForOverdue(odid, queue, type, due, d):
    if odid or queue == 1:
        return
    elif queue == 0 or type == 0:
        return
    elif queue in (2, 3) or (type == 2 and queue < 0):
        diff = due - d.sched.today
        if diff < 0:
            return diff * -1
        else:
            return


def reviewCardPercentageDueString(odid, odue, queue, type, due, ivl):
    if odid:
        due = odue
    if queue == 1:
        return "0"
    elif queue == 0 or type == 0:
        return "0"
    elif queue in (2,3) or (type == 2 and queue < 0):
        try:
            lastRev = due - ivl
            elapsed = mw.col.sched.today - lastRev
            p = elapsed/float(ivl) * 100
            return "{:.1f}".format(p)
        except ZeroDivisionError:
            return "0"
    return "0"


def external_file_link(card, model):
    field_for_filename = ""
    field_for_page = ""
    # import user settings for field names from other add-on
    try:
        field_for_filename = __import__(
            "1994996371"
        ).open_in_external.field_for_filename
        field_for_page = __import__("1994996371").open_in_external.field_for_page
    except:
        return ""
    if all([field_for_filename, field_for_page]):
        note = mw.col.getNote(card.nid)
        for i, f in enumerate(note.model()["flds"]):
            if f["name"] == field_for_filename:
                file = note.fields[i]
            if f["name"] == field_for_page:
                page = note.fields[i]
        try:
            file  # pylint: disable=pointless-statement
            page  # pylint: disable=pointless-statement
        except:
            return ""
        f = stripHTML(file)
        p = stripHTML(page)
        pycmd = f"open_external_filesüöäüöä{f}üöäüöä{p}"
        if p:
            text = f"{f} , {p}"
        else:
            text = f"{f}"
        out = f"""<a href='javascript:pycmd("{pycmd}");'>{text}</a>"""
        return out


def on_field_filter(
    text: str, field: str, filter: str, context: TemplateRenderContext
) -> str:
    if not filter.startswith("info-"):
        return text

    # generate fields if not yet generated
    if "info_fields" not in context.extra_state:
        context.extra_state["info_fields"] = get_all_fields(context)
    info_fields: Dict[str, Any] = context.extra_state["info_fields"]

    # extract the requested field
    info, field = filter.split("-", maxsplit=1)

    return str(info_fields.get(field, f"Unknown field: {field}"))


hooks.field_filter.append(on_field_filter)


def timespan(t):
    """for change from https://github.com/ankitects/anki/commit/89dde3aeb0c1f94b912b3cb2659ec0d4bffb4a1c"""
    if current_point_version < 28:
        return mw.col.backend.format_time_span(t)
    else:
        return mw.col.format_timespan()


def get_all_fields(context: TemplateRenderContext) -> Dict[str, Any]:
    addInfo: Dict[str, Any] = {}
    card = context.card()

    d = mw.col

    if card.odid:
        conf = d.decks.confForDid(card.odid)
    else:
        conf = d.decks.confForDid(card.did)

    if current_point_version < 24:
        (first, last, cnt, total) = mw.col.db.first(
            "select min(id), max(id), count(), sum(time)/1000 from revlog where cid = :id",
            id=card.id,
        )
    else:
        (first, last, cnt, total) = mw.col.db.first(
            f"select min(id), max(id), count(), sum(time)/1000 from revlog where cid = {card.id}"
        )

    addInfo["FirstReview"] = ""
    addInfo["LastReview"] = ""
    addInfo["TimeAvg"] = ""
    addInfo["TimeTotal"] = ""
    addInfo["overdue_fmt"] = ""
    addInfo["overdue_days"] = ""
    if cnt:
        addInfo["FirstReview"] = time.strftime(
            "%a, %d %b %Y %H:%M:%S", time.localtime(first / 1000)
        )
        addInfo["LastReview"] = time.strftime(
            "%a, %d %b %Y %H:%M:%S", time.localtime(last / 1000)
        )

        # https://docs.python.org/2/library/datetime.html  #todo
        addInfo["TimeAvg"] = timespan(total / float(cnt))
        addInfo["TimeTotal"] = timespan(total)

        cOverdueIvl = valueForOverdue(card.odid, card.queue, card.type, card.due, d)
        if cOverdueIvl:
            addInfo["overdue_fmt"] = (
                str(cOverdueIvl) + " day" + ("s" if cOverdueIvl > 1 else "")
            )
            addInfo["overdue_days"] = str(cOverdueIvl)
        addInfo["reviewCardPercentageDue"] = reviewCardPercentageDueString(card.odid, 
                                        card.odue, card.queue, card.type, card.due, card.ivl)

    # addInfo["external_file_link"] = external_file_link(card, context.note_type())

    addInfo["Ord"] = card.ord
    addInfo["Did"] = card.did
    addInfo["Due"] = card.due
    addInfo["Id"] = card.id
    addInfo["Ivl"] = card.ivl
    addInfo["Queue"] = card.queue
    addInfo["Reviews"] = card.reps
    addInfo["Lapses"] = card.lapses
    addInfo["Type"] = card.type
    addInfo["Nid"] = card.nid
    if hasattr(card, "mod"):
        addInfo["Mod"] = time.strftime("%Y-%m-%d", time.localtime(card.mod))
    if hasattr(card, "usn"):
        addInfo["Usn"] = card.usn
    addInfo["Factor"] = card.factor
    addInfo["Ease"] = int(card.factor / 10)

    addInfo["Review?"] = "Review" if card.type == 2 else ""
    addInfo["New?"] = "New" if card.type == 0 else ""
    addInfo["Learning?"] = "Learning" if card.type == 1 else ""
    addInfo["TodayLearning?"] = (
        "Learning" if card.type == 1 and card.queue == 1 else ""
    )
    addInfo["DayLearning?"] = (
        "Learning" if card.type == 1 and card.queue == 3 else ""
    )
    addInfo["Young"] = "Young" if card.type == 2 and card.ivl < 21 else ""
    addInfo["Mature"] = "Mature" if card.type == 2 and card.ivl > 20 else ""
    addInfo["Date_Created"] = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(card.nid / 1000)
    )

    if gc("make_deck_options_available", False):
        addInfo["Options_Group_ID"] = conf["id"]
        addInfo["Options_Group_Name"] = conf["name"]
        addInfo["Ignore_answer_times_longer_than"] = conf["maxTaken"]
        addInfo["Show_answer_time"] = conf["timer"]
        addInfo["Auto_play_audio"] = conf["autoplay"]
        addInfo["When_answer_shown_replay_q"] = conf["replayq"]
        addInfo["is_filtered_deck"] = conf["dyn"]
        addInfo["deck_usn"] = conf["usn"]
        addInfo["deck_mod_time"] = conf["mod"]
        addInfo["new__steps_in_minutes"] = conf["new"]["delays"]
        addInfo["new__order_of_new_cards"] = conf["new"]["order"]
        addInfo["new__cards_per_day"] = conf["new"]["perDay"]
        addInfo["graduating_interval"] = conf["new"]["ints"][0]
        addInfo["easy_interval"] = conf["new"]["ints"][1]
        addInfo["Starting_ease"] = int(conf["new"]["initialFactor"] / 10)
        addInfo["bury_related_new_cards"] = conf["new"]["bury"]
        addInfo["MaxiumReviewsPerDay"] = conf["rev"]["perDay"]
        addInfo["EasyBonus"] = int(100 * conf["rev"]["ease4"])
        addInfo["IntervalModifier"] = int(100 * conf["rev"]["ivlFct"])
        addInfo["MaximumInterval"] = conf["rev"]["maxIvl"]
        addInfo["bur_related_reviews_until_next_day"] = conf["rev"]["bury"]
        addInfo["lapse_learning_steps"] = conf["lapse"]["delays"]
        addInfo["lapse_new_ivl"] = int(100 * conf["lapse"]["mult"])
        addInfo["lapse_min_ivl"] = conf["lapse"]["minInt"]
        addInfo["lapse_leech_threshold"] = conf["lapse"]["leechFails"]
        addInfo["lapse_leech_action"] = conf["lapse"]["leechAction"]

    # add custom fields from user
    td = additional_user_fields(card, conf)
    addInfo = {**addInfo, **td}

    # for debugging quickly
    tt = " <table>" + "\n"
    for k in sorted(addInfo.keys()):
        tt += '<tr><td align="left">%s </td><td align="left">  %s  </td></tr> +\n' % (
            k,
            addInfo[k],
        )
    tt += " </table>" + "\n"
    addInfo["allfields"] = tt

    return addInfo
