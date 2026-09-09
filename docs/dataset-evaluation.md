# Supplied dataset verification

Checks use the local fallback with the full imported corpus; they do not measure Gemini generation quality.

| Question | Result | Seconds |
|---|---|---|
| What does the supplied dataset say about rice flour? | PASS | 1.02 |
| What does the supplied dataset say about laptop computer? | PASS | 2.00 |
| What does the supplied dataset say about domestic plug? | PASS | 1.04 |
| What does the supplied dataset say about Portland cement? | PASS | 1.96 |
| What does the supplied dataset say about cotton yarn? | PASS | 0.89 |
| What does the supplied dataset say about passenger-car tyre? | PASS | 0.97 |
| What does the supplied dataset say about laundry detergent powder? | PASS | 2.72 |
| What does the supplied dataset say about hexagon bolt? | PASS | 0.98 |
| What does the supplied dataset say about examination glove? | PASS | 1.66 |
| What does the supplied dataset say about spade? | PASS | 0.88 |
| What is the licence status and holder for DEMO-LIC-FOD-001? | PASS | 1.65 |
| What does IS 3024:2015 cover? | PASS | 0.75 |
| Explain the scope of IS 13252 (Part 1):2010 | PASS | 1.99 |
| Show the status for DEMO-LIC-FOD-999 | PASS | 0.44 |

14/14 checks passed.

Imported dataset: 500 synthetic documents and 21 reference documents, containing 3,677 passages.

Repeated import: 521 documents recognized, zero new chunks; existing citation targets preserved.

Live API check: licence status and holder matched the dataset, with a product-name heading and a brief synthetic-source note. Gemini returned a quota error, so the live answer used the local fallback.
