# Executive summary

**MandiMitra — explainable mandi price intelligence.** Vishnu Keer, Vivekananda
Global University, Jaipur. Live: <https://mandimitra.streamlit.app/> · Code and
data: <https://github.com/vishnu-keer/mandimitra>

**Problem.** Mandi prices jump without warning (Jaipur onion: Rs. 600–900/q in
June 2013, Rs. 4,500 on 21 Oct 2013), and AI price-prediction claims reach
farmers and traders without any visible test of whether they beat the simplest
forecast — "tomorrow's price = today's price".

**What we built.** A free, open-source pipeline and bilingual (English/Hindi)
dashboard on official Department of Consumer Affairs daily wholesale prices
(Onion and Tomato, Jaipur, 2009–2015). Five methods are compared with a
protocol that chooses the model on earlier years and scores unseen data once.
The dashboard puts the reference forecast, data freshness, stale-quote rates
and honest uncertainty in front of the user. A tested client for the official
AGMARKNET daily price API is ready for current data once a free access key is
added.

**What we found (measured).**

- The model chosen in advance never beat "same as today" on unseen data
  (Onion: Naive chosen at all horizons; Tomato: −5.66%, −0.53%, −0.31%).
- 0 of 48 significance tests found any model more accurate than Naive.
- Our own first version claimed "+7.33%" by picking the winner on the test
  data; that gap has p = 0.505.
- 83–85% of reported days repeat the previous price; 80% ranges covered only
  55–74% of outcomes, so none are drawn.

**Why it matters.** Before anyone acts on a price prediction, it should beat
the simplest reference on data it never saw. MandiMitra makes that check
visible, reproducible and understandable.

**Status.** Working, deployed, 154 automated tests, CI green, ₹0 running cost.
No user study yet — no impact is claimed. Next: current data, more markets,
arrivals/rainfall inputs, a consented user study.
