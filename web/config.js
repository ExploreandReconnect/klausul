/* The API origin. Absolute, so the same file works whether the page is served
   by Render itself or from GitHub Pages.

   ?api=https://… in the address bar overrides this, which is handy for testing.
   Leave it empty and the page still works in full on the cached example — it
   simply cannot read a document it has not seen before. */
window.KLAUSUL_API = "https://klausul-api.onrender.com";
