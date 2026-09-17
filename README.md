# 🎨 Jev Art

Type some words. Get a picture. That's it.

Type something like **"sunset over the sea"** or **"a spooky forest"**, press a button,
and a piece of moving 3D art appears in your web browser. A smart helper called **Jev**
reads the mood of your words (warm or cold? busy or calm? bright or dark?) and the
picture is built from that.

---

## 🔑 Step 1 — Add your secret key (you only do this once)

This app needs a **secret key** (think of it like a password) to work.

1. In this folder, find the file named **`.env.example`**.
2. Make a copy of it and rename the copy to **`.env`** (yes, just a dot and the word "env").
3. Open **`.env`** with any text editor.
4. Put your secret key right after the `=` sign, then save and close.

It should look like this:

```
TYPESAFE_API_KEY=your-secret-key-goes-here
```

> **Don't have a key yet?**
> Sign up for the waitlist at https://typesafe.ai — you'll get access to Jev soon.
> Once you're in, grab your key from https://console.typesafe.ai/settings/keys and paste it in above.

---

## ▶️ Step 2 — Start the app

**Easiest way (Mac):** double-click the file **`start.command`**.

- A black window will open. That's normal — just leave it open.
- Your web browser will open by itself and show the app.

*(If double-clicking says it "cannot be opened", right-click `start.command` →
click **Open** → click **Open** again. You only need to do that once.)*

**Or, if you like typing:** open the Terminal app, and type:

```
python3 serve.py
```

Then open your browser and go to **http://localhost:8000**

---

## 🖼️ Step 3 — Make art!

1. Type any words into the box.
2. Click **Generate**.
3. Wait a moment… and watch your art appear!
4. **Click and drag** the picture to spin it around. 🌀

Try lots of different words. Happy, sad, hot, cold, calm, wild — each one looks different.

---

## ⏹️ How to stop

Close the black window (or press **Control + C** in it).

---

## 🙋 Something not working?

- **Nothing happens / error about a key** → check Step 1. Make sure the file is named exactly `.env` and your key is pasted in.
- **Browser didn't open** → open it yourself and go to http://localhost:8000
- **"python3 not found"** → your Mac needs Python. Open Terminal, type `python3 --version`; if it asks to install developer tools, click **Install**.

That's everything. Have fun. 🎉
