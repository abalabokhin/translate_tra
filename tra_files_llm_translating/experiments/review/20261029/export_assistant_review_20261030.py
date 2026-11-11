"""Attach assistant-authored editorial proposals to saved replies; never edit experiment data.

This is a dated review artifact, not a translation repair mechanism or a scoring
rule. Proposals below are complete, manually written alternatives. Human approval
is pending. Re-running refuses to overwrite review files or user notes.
"""
import collections
import csv
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parents[1]
BASE = EXPERIMENTS / 'prompt_ab/20261029-212402'
REAL = EXPERIMENTS / 'prompt_ab/20261029-220151-recovered'
VERIFY = EXPERIMENTS / 'translate_verify/20261030-095325'


def assess(dataset, line, gender, text):
    """Editorial judgments on this dated batch, not general linguistic detection."""
    female = gender == 'female'
    categories, notes, proposal = [], [], ''

    def flag(category, reason, complete_line=''):
        nonlocal proposal
        categories.append(category)
        notes.append(reason)
        if complete_line:
            proposal = complete_line

    if dataset == 'inkgallery':
        if line == '@16':
            if 'рады' in text:
                flag('grammar', 'Singular Галерея has plural predicate рады.')
            if text.startswith('Здравствуйте'):
                flag('register', 'Formal/plural greeting conflicts with singular ты register.')
            if female and 'приключенец' in text:
                flag('player_gender', 'Masculine address noun retained for female Player1.')
            if categories:
                flag('editorial_proposal', 'Complete alternative preserves greeting and gallery tales.',
                     ('Здравствуй снова, искательница приключений. Наша Галерея Чернил приветствует тебя своими историями.'
                      if female else 'Здравствуй снова, искатель приключений. Наша Галерея Чернил приветствует тебя своими историями.'))
        elif line == '@48':
            if female and 'зашёл' in text:
                flag('player_gender', 'Missed feminine зашла.')
            if 'Разве' in text:
                flag('meaning', 'Unless exception becomes a разве construction; final period also conflicts with interrogative wording.')
            if categories:
                flag('editorial_proposal', 'Preserve the unless condition and singular addressee.',
                     ('Нам стоит поговорить внизу. Если только ты не зашла просто узнать, как у меня дела.'
                      if female else 'Нам стоит поговорить внизу. Если только ты не зашёл просто узнать, как у меня дела.'))
        elif line == '@100' and female and ('видел' in text or 'пришёл' in text):
            flag('player_gender', 'Both видел and пришёл refer to female Player1; both need correction.',
                 'Привет, <CHARNAME>! Ты уже видела все мои книги, но, может, ты пришла за сувенирами?')
        elif line in ('@17', '@24') and ('Так что я понял' in text or 'Так что я поняла' in text):
            flag('grammar', 'From what I understood needs a parenthetical как я понял/поняла, not this unconnected opening.',
                 ('Да. ' if line == '@24' else '') +
                 ('Как я поняла, заплатив сбор, я смогу испытать себя в битвах, описанных в этих книгах. Это так?'
                  if female else 'Как я понял, заплатив сбор, я смогу испытать себя в битвах, описанных в этих книгах. Это так?'))
        elif line == '@19':
            flag('meaning' if 'выучу' in text else 'idiom',
                 'Learn from books means gaining knowledge, not memorizing all books; научусь у книг is also awkward.',
                 'Что произойдёт, если я успешно усвою знания из всех этих книг?')
        elif line == '@20':
            flag('terminology_review', 'Cowled Wizards lacks an exact glossary entry. Капюшонные Волшебники needs a chosen game glossary; no canonical replacement imposed.')

    elif dataset == 'multiple_npcs':
        if line == '102' and text.startswith('Селене,'):
            flag('grammar', 'Direct address requires Селена, not dative Селене.',
                 'Селена, ты была права. Я слишком поспешил, обвиняя его.')
        elif line == '105' and female:
            flag('player_gender', 'Female traveler is addressed as masculine странник. Orin remains male: обязан stays unchanged.',
                 'Ты спасла её, странница. Я обязан тебе жизнью.')
        elif line == '106':
            flag('meaning', 'Meet us at dawn is an instruction to Orin; Встретимся leaves the explicit us implicit.',
                 'Тогда сдержи своё обещание, Орин. Встреться с нами на рассвете.')
        elif line == '101':
            flag('minor_addition', 'Waiting for you is plausible, but source only says Orin was waiting downstairs. Low priority.',
                 ('Ты вернулась, <CHARNAME>. Орин ждал внизу.' if female
                  else 'Ты вернулся, <CHARNAME>. Орин ждал внизу.'))

    elif dataset == 'reused_strings':
        if line in ('301_a', '301_b') and not female:
            flag('shared_string', 'One TRA key is spoken by female Selene and male Player1. Neither готов nor готов(а) is suitable natural shared wording.',
                 'Я наготове.')
        elif line in ('302_a', '302_b'):
            flag('address_form', 'Source metadata names Selene as the singular addressee.', 'Тогда открой ворота.')
        elif line == '304':
            flag('address_form', 'Source metadata names Player1 as the singular addressee; group address is not needed here.',
                 'Подожди <CHARNAME>.\nНе трогай %gate_lock%.')

    elif dataset == 'inkgallery_beholder':
        if line == '100_INITIAL_0_SAY_0':
            if 'Нежить и дикий' in text:
                flag('grammar', 'Parallel undead/wild description mixes a noun with an adjective.')
            if 'мёртвая зона магии' in text:
                flag('check_limitation', 'Understandable dead-magic-zone wording; frozen regex likely overrejects it. No score changed.')
            flag('terminology_review', 'Созерцатель versus бехолдер requires glossary choice; no canonical replacement imposed.')
            if 'Нежить и дикий' in text:
                flag('editorial_proposal', 'Complete proposal retains quotes, past narration and dead magic.',
                     '"Гниющий шар висел в центре влажной пещеры. Зомби-созерцатель, которого считали мёртвым на протяжении века, а может, и дольше. Неживой и дикий одновременно. Когда он видел какое-либо живое существо, то кусал его своей мощной пастью. Это область мёртвой магии, поэтому он привык сражаться с несчастными своими острыми зубами."')
        elif line == '100_BLOCK_0_ELEMENT_0_SAY_1' and 'заслуженно уничтожить' in text:
            flag('grammar', 'Его заслуженно уничтожить is an incomplete predicate.',
                 'Зомби-созерцатель? И, скорее всего, разъярённый. Он заслуживает уничтожения, и именно это мы должны с ним сделать.')
        elif line == '100_BLOCK_1_ELEMENT_0_SAY_2':
            flag('grammar_idiom', 'Learning sentence has incomplete узнает or awkward учиться из/у книги; payment phrasing also needs editing.')
            if 'женщина' in text or 'героиня' in text:
                flag('meaning_gender', 'The selected learner may be <PLAYER2>–<PLAYER6>; female Player1 does not make every selectable fighter female.')
            flag('editorial_proposal', 'Same selected person remains gender unspecified. Prices and one-on-one restriction preserved.',
                 'С этим существом можно сразиться только один на один. Поэтому плата составляет не 3500 золотых, а немного меньше: за 3000 монет ты сможешь с ним сразиться. Знания из этой книги получит тот же человек.')
        elif line == '100_BLOCK_1_ELEMENT_0_REPLY_3':
            flag('idiom', 'Только справедливо is a calque for it is only fair.')
            if female:
                flag('register_policy', 'Leader title should be reviewed under complete-agreement policy. Masculine role nouns with feminine predicates can occur in Russian; лидерша is a register choice, not proof of a universal grammar rule.')
            flag('editorial_proposal', 'Complete alternative retains initial leadership and explicit token.',
                 ('Хорошо. Будет справедливо, если с этой тварью сразится первоначальная предводительница, <PLAYER1>.'
                  if female else 'Хорошо. Будет справедливо, если с этой тварью сразится первоначальный предводитель, <PLAYER1>.'))
        elif line == '100_BLOCK_1_ELEMENT_0_REPLY_9':
            flag('style_optional', 'Я пропущу is understandable; direct refusal is more idiomatic in this encounter.',
                 'Нет. Я откажусь. По крайней мере пока.')

    elif dataset == 'inkgallery_moon_sisters':
        if line == '000_INITIAL_0_SAY_0':
            flag('idiom', 'Пришёл/пришла за судом is awkward for coming to judgment.',
                 ('Ты пришла сюда. Ты пришла предстать перед судом Сестёр Луны! Мы — КОСМОС, наполняющий это место.'
                  if female else 'Ты пришёл сюда. Ты пришёл предстать перед судом Сестёр Луны! Мы — КОСМОС, наполняющий это место.'))
        elif line in ('000_BLOCK_0_ELEMENT_0_SAY_1', '001_BLOCK_2_ELEMENT_0_SAY_11'):
            flag('terminology_review', 'DREAMS permits мечты or сны here; preserve a consistent chosen reading, not a mandatory reference spelling.')
        elif line == '000_BLOCK_2_ELEMENT_0_SAY_3' and 'по причине,' in text:
            flag('idiom', 'Bare по причине is incomplete for for a reason.',
                 ('Ты пришла сюда не просто так, но… странно. Ты не та душа, которую мы ожидали. Нет. Ты нечто иное.'
                  if female else 'Ты пришёл сюда не просто так, но… странно. Ты не та душа, которую мы ожидали. Нет. Ты нечто иное.'))
        elif line == '000_BLOCK_3_ELEMENT_0_SAY_4':
            flag('title_review', 'Bloodied means blood-stained; Кровавый may instead suggest bloodthirsty. Девочка also narrows the fantasy Child title. Ребёнок can grammatically denote a girl.',
                 'Ты — Окровавленное Дитя.')
        elif line == '000_BLOCK_4_ELEMENT_0_REPLY_6' and female:
            flag('player_gender', 'Настоящего/истинного меня remains masculine for female Player1. The frozen check misses истинного.',
                 'Это странно. Кажется, будто вы видите настоящую меня, а не персонажа из этой книги.')
        elif line == '001_BLOCK_0_ELEMENT_0_SAY_9' and 'Это достаточно' in text:
            flag('grammar', 'Use Этого достаточно for this sufficiency construction. Masculine путь отмечен is already correct.',
                 'Но мы по-прежнему Сестры Луны, и мы можем видеть сквозь КОСМОС. Твой путь отмечен кровью. Этого достаточно, чтобы мы знали, что твою руку нужно остановить.')
        elif line == '001_BLOCK_1_ELEMENT_0_SAY_10':
            flag('grammar_idiom', 'Nonidiomatic plural свои оружия; use collective оружие.', 'Сёстры! Возьмите оружие!')

    elif dataset == 'inkgallery_sewers':
        if line == '100_INITIAL_0_SAY_0':
            flag('grammar_idiom', 'At least not these tunnels becomes broken или хотя бы не эти туннели. Keep the narrated adventurer male.',
                 '"Одинокий авантюрист, оставленный и преданный своей группой, пробирался сквозь слои слизи и сточных вод. Все его бывшие друзья думали, что он мёртв, но он всегда был упрямым, и у него ещё оставались несколько козырей в рукаве. Он выжил. Но канализация не была безопасным местом — по крайней мере эти туннели. Недавно их захватили странные червеобразные существа. Они уже знали, что он там, и готовились к атаке."')
        elif line == '100_BLOCK_1_ELEMENT_0_SAY_2':
            flag('grammar_idiom', 'English-style один-на-один бой needs Russian word order.',
                 'Это бой за выживание один на один. Плата за изучение большинства этих книг составляет 3500 золотых монет, но использование этой книги стоит всего 3000 золотых монет.')
        elif line == '100_BLOCK_1_ELEMENT_0_REPLY_3':
            flag('meaning_idiom', 'Оригинальный means unusual/original in another sense; here original leader means initial leader. Только справедливо is also a calque.',
                 'Хорошо. Будет справедливо, если с этими существами сразится первоначальный предводитель, <PLAYER1>.')
        elif line in [f'100_BLOCK_1_ELEMENT_0_REPLY_{n}' for n in range(4, 9)]:
            token = {'100_BLOCK_1_ELEMENT_0_REPLY_4': '<PLAYER2>', '100_BLOCK_1_ELEMENT_0_REPLY_5': '<PLAYER3>',
                     '100_BLOCK_1_ELEMENT_0_REPLY_6': '<PLAYER4>', '100_BLOCK_1_ELEMENT_0_REPLY_7': '<PLAYER5>',
                     '100_BLOCK_1_ELEMENT_0_REPLY_8': '<PLAYER6>'}[line]
            flag('meaning_idiom', 'Вещи weakly renders the worm-like creatures; combat selection is clearer than mere столкнётся.',
                 f'Хорошо. Пусть с этими существами сразится {token}.')
        elif line == '100_BLOCK_1_ELEMENT_0_REPLY_9':
            flag('style_optional', 'Direct refusal is more idiomatic than Я пропущу.', 'Нет. Я откажусь. По крайней мере пока.')

    return '; '.join(dict.fromkeys(categories)), ' '.join(notes), proposal


def main():
    rows, sources, counts = [], [], collections.Counter()
    logs = sorted(BASE.glob('*/runs.jsonl')) + sorted(REAL.glob('*/runs.jsonl'))
    logs += [VERIFY / 'translate-verify/inkgallery/translation/runs.jsonl']
    for log in logs:
        raw = log.read_bytes()
        records = [json.loads(s) for s in raw.decode().splitlines()]
        dataset = 'inkgallery' if log.parent.name == 'translation' else log.parent.name
        run = VERIFY if log.parent.name == 'translation' else log.parent.parent
        snapshot = run / 'snapshot/tra_files_llm_translating'
        if dataset == 'inkgallery':
            inputs = snapshot / 'examples/inkgallery-json-two-pass/input.csv'
        else:
            inputs = snapshot / 'experiments' / ('real_set' if dataset.startswith('inkgallery_') else 'fixtures') / dataset / 'input.csv'
        with inputs.open(encoding='utf-8-sig', newline='') as handle:
            lines = list(csv.DictReader(handle))
        sources.append(dict(path=str(log.relative_to(EXPERIMENTS)), sha256=hashlib.sha256(raw).hexdigest(),
                            records_at_review=len(records), input_sha256=hashlib.sha256(inputs.read_bytes()).hexdigest()))
        for record in records:
            if record.get('error') or not record.get('translations'):
                counts['excluded_failed_or_skipped_records'] += 1
                continue
            counts['reviewed_reply_records'] += 1
            for line in lines:
                key, gender = line['Line_ID'], record['gender']
                text = record['translations'][key]
                english = line['Dialogue_Text']
                if gender == 'female' and (line.get('Source_Has_Female') == '1' or line.get('Source_Female_Text')):
                    english = line['Source_Female_Text']
                categories, notes, proposal = assess(dataset, key, gender, text)
                if not english.strip():
                    assert text == '', 'Explicit empty source must stay empty'
                    notes = 'Explicit empty female source correctly exported empty; excluded from female model request.'
                rows.append(dict(Dataset=dataset, Run=str(run.relative_to(EXPERIMENTS)),
                                 Prompt=record['config']['prompt'], Repeat=str(record['config']['repeat']),
                                 Gender=gender, Line_ID=key, Actor=line['Actor'],
                                 Predecessors=line['Predecessors'], Source=line.get('Additional_Info', ''),
                                 English=english, Model_Russian=text,
                                 Assessment=categories or 'no_issue_identified', Assistant_Notes=notes,
                                 Proposed_Complete_Line=proposal, User_Review=''))
    output = HERE / 'ASSISTANT_REVIEW_2026-10-30.csv'
    with output.open('x', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with output.open(encoding='utf-8-sig', newline='') as handle:
        assert list(csv.DictReader(handle)) == rows
    meta = dict(reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                reviewer='assistant; human approval pending', counts=dict(counts), cells=len(rows),
                proposed_cells=sum(bool(r['Proposed_Complete_Line']) for r in rows),
                source_snapshots=sources, review_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                scope='Saved translation replies only. No Gemma verifier or planted controls reviewed. Failed replies excluded, preserved in raw logs.',
                policy='Editorial proposals only; no changes to raw output, references, scores, glossary or production files.')
    with output.with_suffix('.meta.json').open('x') as handle:
        json.dump(meta, handle, indent=2)
        handle.write('\n')
    print(json.dumps({k: meta[k] for k in ('counts', 'cells', 'proposed_cells')}, indent=2))


if __name__ == '__main__':
    main()
