# Deploy — 15 minutes, €0/month

Two halves. The **page** is static and lives on GitHub Pages. The **API** is a
container on Render's free plan. They are in the same repo.

The page renders in full on cached example data, so it is instantly available even
when the API is asleep. The API is only woken when someone uploads their own
documents — a person who is already expecting to wait for a model.

---

## 1 · Push the repo  (3 min)

Create a new **public** repository on GitHub — public is required by the hackathon
rules, and it is also what makes GitHub Pages free.

Drag the contents of this folder into it, or:

```bash
git init && git add -A
git commit -m "Klausul: EU motor insurance, evidence-bound"
git branch -M main
git remote add origin https://github.com/<you>/klausul.git
git push -u origin main
```

> `.gitignore` already excludes `.env`, so your key cannot travel with the code.
> Check once before pushing: `git status --porcelain | grep -i env` should print nothing.

## 2 · Turn on Pages  (2 min)

**Settings → Pages → Source: GitHub Actions.**

That is all. `.github/workflows/pages.yml` publishes `web/` on every push. Your page
appears at `https://<you>.github.io/klausul/` within a minute or two.

**This URL alone satisfies the "working demo URL" requirement** — it shows the entire
product on the cached example. Everything below adds live uploads.

## 3 · Deploy the API  (5 min)

1. [render.com](https://render.com) → **New** → **Blueprint**
2. Point it at the repo. It reads `render.yaml` and finds the `Dockerfile`.
3. It will ask for **`NEBIUS_API_KEY`** — paste your Token Factory key there.
   `sync: false` in the blueprint is what makes Render prompt instead of storing it
   in the repo. **The key never goes in a file.**
4. First build takes a few minutes. When it is green, note the URL, e.g.
   `https://klausul-api.onrender.com`

Check it answers honestly:

```bash
curl https://klausul-api.onrender.com/health
# {"ok":true,"live":true,"model_extract":"nvidia/nemotron-3-super-120b-a12b",...}
```

`"live": true` means the key is present. If it says `false`, the key did not save.

## 4 · Introduce them  (2 min)

Edit **`web/config.js`**, one line:

```js
window.KLAUSUL_API = "https://klausul-api.onrender.com";
```

Commit and push. Pages redeploys itself.

Then tighten CORS: in Render, set `KLAUSUL_ALLOWED_ORIGINS` to your exact Pages
origin (`https://<you>.github.io`) instead of `*`.

## 5 · Check it end to end  (3 min)

Open the page → **A** → upload `demo/Bilforsikring_2025.pdf` and
`demo/Fornyelse_2026.pdf` → country **Denmark** → *Read both documents*.

The first run after the API has been idle takes up to a minute while Render wakes
the container. The chip at the top of the result must read **Live**, not
**Illustrative** — if it still says Illustrative, `config.js` did not take.

---

## What costs what

| | Plan | Cost |
|---|---|---|
| GitHub Pages | Public repo | **€0** |
| Render web service | Free | **€0** |
| Nebius Token Factory | Your promo credits | **€0** until they run out |
| Database | **None needed** | **€0** |

The app is stateless: two PDFs in, one comparison out, nothing stored. There is no
session, no account, no saved history — so there is nothing for a database to hold.

---

## Testing without deploying

```bash
pip install -r requirements.txt
export NEBIUS_API_KEY=...
uvicorn app.main:app --reload        # page and API together at localhost:8000
```

Or point the published page at a local API for one request:
`https://<you>.github.io/klausul/?api=http://localhost:8000`

---

## The one thing to get right

The chip at the top of the result tells the reader which world they are in —
**Illustrative** (cached example) or **Live** (their own documents). Your design
constitution says a `live` chip on mock data is the one thing that must never ship.
It is wired to the actual data source, not to a flag. Leave it that way.
