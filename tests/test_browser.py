import asyncio
import json
import os
from urllib.parse import urlparse

from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'docs/index.html').read_text()
BASE_URL=os.environ.get('SPI_BASE_URL')
# Browser navigation to local files is blocked by the environment. Use an in-memory
# document for UI verification; a small storage double is test-only, never shipped.
STORAGE="""<script>if(!window.__testStore){window.__testStore=new Map();Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>window.__testStore.get(k)??null,setItem:(k,v)=>window.__testStore.set(k,String(v)),removeItem:k=>window.__testStore.delete(k)}});}</script>"""
TESTHTML=SOURCE.replace('<script>',STORAGE+'<script>',1)

Q=json.loads((ROOT/'dist/questions.json').read_text())

async def refresh(page):
    if BASE_URL:
        await page.reload()
        return
    entries=await page.evaluate('Array.from(window.__testStore.entries())')
    await page.goto('about:blank')
    await page.set_content(TESTHTML.replace('new Map()', 'new Map('+json.dumps(entries)+')', 1))

async def run():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-crashpad-for-testing'])
        context=await browser.new_context(viewport={'width':1280,'height':1000},accept_downloads=True)
        page=await context.new_page()
        errors=[];requests=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        page.on('request',lambda r: requests.append(r.url))
        page.on('dialog',lambda d: asyncio.create_task(d.accept()))
        if BASE_URL:await page.goto(BASE_URL)
        else:await page.set_content(TESTHTML)
        await page.screenshot(path=str(ROOT/'dist/preview-desktop.png'),full_page=True)
        assert await page.locator('h1').inner_text()=='好きなだけ、\n少しずつ。'
        # Choose 5, answer wrong, flag a correct answer, and finish the session.
        await page.locator('[data-action=count][data-value="5"]').click()
        await page.locator('[data-action=start]').click()
        assert await page.locator('#submit-answer').is_disabled()
        await page.set_viewport_size({'width':390,'height':844})
        for i in range(5):
            assert await page.locator('.practice-top').inner_text()
            qid=(await page.locator('.q-meta .number').inner_text()).split(' · ')[-1].lower()
            q=next(q for q in Q if q['id']==qid)
            answer=(q['answer']+1)%len(q['choices']) if i==0 else q['answer']
            await page.locator(f'input[name=answer][value="{answer}"]').check()
            if i==1:await page.locator('#unsure').check()
            await page.locator('#submit-answer').click()
            assert await page.locator('#verdict').count()==1
            assert await page.locator('input[name=answer]:enabled').count()==0
            if i==0:
                assert await page.locator('.answer.incorrect').evaluate("el=>getComputedStyle(el).backgroundColor")=="rgb(255, 244, 241)"
                await page.screenshot(path=str(ROOT/'dist/preview-mobile.png'),full_page=True)
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            await page.locator('[data-action=next]').click()
        assert await page.locator('.score').inner_text()=='4/ 5問 正解'
        snap=await page.evaluate('SPI.snapshot()')
        assert sum(r['attempts'] for r in snap['records'].values())==5
        assert sum((not r['lastCorrect'] or r['unsure']) for r in snap['records'].values())==2
        await page.locator('[data-action=home]').last.click()
        await refresh(page)
        assert await page.evaluate('SPI.snapshot()')==snap
        await page.locator('[data-action=review]').click()
        assert '1 / 2問' in await page.locator('.practice-top').inner_text()
        # Find the correct choice by the question content and remove the review flag.
        qid=(await page.locator('.q-meta .number').inner_text()).split(' · ')[-1].lower()
        q=next(q for q in Q if q['id']==qid)
        await page.locator(f'input[name=answer][value="{q["answer"]}"]').check()
        await page.locator('#submit-answer').click()
        assert not (await page.evaluate('SPI.snapshot()'))['records'][q['id']]['unsure']
        # A graded answer survives early exit.
        await page.locator('[data-action=leave]').click()
        assert await page.locator('.score').inner_text()=='1/ 1問 正解'
        await page.locator('#nav [data-action=records]').click()
        assert await page.locator('[data-action=export],#import-file').count()==0
        assert 'ブラウザのデータを削除すると記録も消えます' in await page.locator('#app').inner_text()
        await page.locator('[data-action=reset]').click()
        assert await page.evaluate('Object.keys(SPI.snapshot().records).length')==0
        await page.locator('#nav [data-action=topics]').click()
        assert await page.locator('.topic-card').count()==15
        await page.locator('[data-action=count][data-value=all]').click()
        await page.locator('[data-action=topic]').first.click()
        assert '1 / 40問' in await page.locator('.practice-top').inner_text()
        await page.locator('[data-action=leave]').click()
        await page.locator('[data-action=count][data-value="20"]').click()
        await page.locator('[data-action=start]').click()
        assert '1 / 20問' in await page.locator('.practice-top').inner_text()
        # Keyboard choice/submit interaction works without a mouse.
        await page.evaluate('new Promise(requestAnimationFrame)')
        await page.locator('input[name=answer]').first.focus()
        await page.keyboard.press('Space')
        assert await page.locator('#submit-answer').is_enabled()
        await page.locator('#nav [data-action=topics]').click()
        await page.locator('[data-action=topic][data-value="仕事算"]').click()
        qid=(await page.locator('.q-meta .number').inner_text()).split(' · ')[-1].lower()
        q=next(q for q in Q if q['id']==qid)
        await page.locator(f'input[name=answer][value="{q["answer"]}"]').check()
        await page.locator('.question-card').screenshot(path=str(ROOT/'dist/preview-mobile-question.png'))
        await page.locator('#submit-answer').click()
        assert await page.locator('.solution-steps>li').count()==4
        assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        await page.locator('.solution-steps').screenshot(path=str(ROOT/'dist/preview-mobile-explanation.png'))
        await page.screenshot(path=str(ROOT/'dist/preview-mobile.png'),full_page=True)
        assert not errors, errors
        if BASE_URL:assert all(urlparse(url).netloc==urlparse(BASE_URL).netloc for url in requests),requests
        else:assert not requests,requests
        # Corrupt stored data is preserved, with an explicit visible notice.
        await page.evaluate("localStorage.setItem('spi-practice-v1','broken-json')")
        await refresh(page)
        assert '読み取れません' in await page.locator('#notice').inner_text()
        await page.locator('[data-action=start]').click()
        await page.locator('input[name=answer]').first.check()
        await page.locator('#submit-answer').click()
        assert await page.evaluate("localStorage.getItem('spi-practice-v1')")=='broken-json'
        await context.close()
        # A browser that refuses storage can still answer in-memory.
        context2=await browser.new_context()

        page2=await context2.new_page()
        await page2.set_content(SOURCE)
        await context2.set_offline(True)
        assert '保存できません' in await page2.locator('#notice').inner_text()
        await page2.locator('[data-action=start]').click()
        await page2.locator('input[name=answer]').first.check()
        await page2.locator('#submit-answer').click()
        assert await page2.evaluate('Object.keys(SPI.snapshot().records).length')==1
        await browser.close()
        print('Browser UI in memory (storage double): web UI, desktop/mobile, grading, review, persistence, reset, keyboard, corrupt data and blocked storage passed.')

asyncio.run(run())
