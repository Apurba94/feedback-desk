# Feedback Desk

A simple, offline way for a field team to record what communities tell them, respond on time, and show that responses happened. It is built around one idea: a feedback system only counts if the loop closes.

```
python -m feedback_desk
```

Then open http://127.0.0.1:8033. It needs Python 3.10 or newer.

## What it does

- **Case records** with a type, channel, topic and area
- **Response deadlines** by type, with overdue flags
- **Closing the loop:** a case cannot be marked answered without recording what the person was told
- **Reports:** answer rate, share on time, cases per week and topics that are rising fast
- **Safe sharing:** small numbers are hidden in shareable tables, including a second cell where subtraction would reveal one

## Sensitive cases: designed for safety

Reports of abuse, exploitation or danger must go to a trained focal point straight away, through your safeguarding procedure. **This app is not the place for those details,** because its file is not encrypted.

So it enforces a rule. A sensitive case records only a code and who it was referred to, and any details typed for it are refused. If an ordinary case contains warning words in English or Bangla, saving stops until someone has checked. Phone numbers are removed from saved summaries.

The word list is a small aid. It will miss many cases and flag some harmless ones, so it cannot replace staff training.

Read this with your organisation's safeguarding and data protection leads before use. This is an independent project, and it is not endorsed by any humanitarian organisation.

## How it is tested

Deadlines, states and performance numbers are checked at their boundaries. Tests confirm that details of a sensitive case are refused at entry and on update, that a warning word stops saving, and that a lone small number cannot be worked out by subtraction.

## Limits

One computer, with no logins, so anyone at it can read ordinary cases. Summaries could still contain names if staff type them, so train staff not to. There is no SMS or hotline link. Topics are free text, so spelling differences split the counts.

## Tests

```
python -m unittest discover -s tests
```

MIT licence.
