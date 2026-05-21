# staging -> develop Carryback Inventory (2026-05-21)

## Done Today

- Session reload / stale load fixes
  - `85b18c7` Guard production session state against stale loads
  - `94260a8` Guard incomplete session risk-at-time responses
  - `6dac81c` Always return mesh coords from risk endpoint
  - `91fbeb1` Refetch prefecture data for new sessions
- Prefecture ordering / session payload fixes
  - `7fd7799` Load prefectures from CSV master
  - `8b3763d` Align rainfall modal prefecture order
  - `6135dbe` Use session payload for rainfall modal order
- Carryback-only follow-up
  - `87d94a4` Align carried-back risk endpoint behavior

## Remaining Mainline Candidates

- Cache / session hardening
  - `698d6ed`
  - `813f65c`
  - `6a4bc9c`
  - `4b79bfc`
  - `c4c273a`
  - `1017d28`
  - `1ca02a2`
  - `f59e7f6`
  - `2109e4a`
  - `eb2f4ee`
  - `f15940c`
  - `3f065c5`
  - `8a9b5da`
  - `7912b8f`
  - `12572f6`
- Rainfall / risk-rule / GSM
  - `0d24d51`
  - `4eae356`
  - `a23a77f`
  - `3f3ae4e`
  - `4b6e295`
  - `a44063e`
  - `bda6282`
  - `b1b2293`
  - `abf1e61`
  - `0806ded`
  - `a733d98`

## staging-only / Do Not Carry Back

- Deploy / Apache / route-profile / proxy
  - `107b841`
  - `33ac6d9`
  - `8eb309b`
  - `e799207`
- Promotion cleanup / staging packaging
  - `6477b54`
- Investigation-only traces / production debug logging
  - `429376b`
  - `8a39395`
  - `8513afa`
- Local investigation artifacts
  - `server/data/2nd.txt`
  - `server/data/3rd.txt`

## Notes

- `35f966e` is superseded by later session fixes and should not be carried alone.
- Remaining mainline candidates should be carried in grouped PRs, not mixed with staging-only changes.
