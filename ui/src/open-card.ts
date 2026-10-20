// Opening a card from outside the page (the blocked-card toast): Desktop's router owns the address, so the card id rides
// the route's query, "#/crew?card=<id>". A fresh stamp per link makes a second link to the same card a changed hash, so
// the page sees it again after the owner went back to the board.
export const CREW_ROUTE = '/crew'

export const cardLink = (id: string, stamp: number = Date.now()): string =>
  CREW_ROUTE + '?card=' + encodeURIComponent(id) + '&n=' + stamp

const CARD_ID = /^[A-Za-z0-9_-]+$/

// The card id of a location hash ("#/crew?card=t_x&n=1"), or '' when the hash opens no card.
export function cardFromHash(hash: string): string {
  const m = /^#?\/crew\?(.*)$/.exec(hash || '')
  const id = m ? new URLSearchParams(m[1]).get('card') || '' : ''
  return CARD_ID.test(id) ? id : ''
}

// The card id of a location query ("?card=t_x"), or '' when the query opens no card: what a freshly loaded shareable
// link to a hosted Crew tab carries (cardUrl below).
export function cardFromSearch(search: string): string {
  const id = new URLSearchParams((search || '').replace(/^\?/, '')).get('card') || ''
  return CARD_ID.test(id) ? id : ''
}

// The shareable link to card `id`, built from the board's resolved link (Board.resolveDashboardLink). One convention,
// read back by every page that can receive it:
//   a hosted Crew tab (a link ending in "/crew": Desktop's gateway, the Hermes web dashboard tab) -> "<tab>?card=<id>",
//     read on arrival with cardFromSearch by the Desktop page (CrewPage) and the dashboard tab (browser.tsx);
//   the served shell (any other link) -> "<origin>/card/<id>", read by route.parseLocation.
export function cardUrl(dashLink: string, id: string): string {
  const base = (dashLink || '').trim().replace(/\/+$/, '')
  const enc = encodeURIComponent(id)
  return base.endsWith(CREW_ROUTE) ? base + '?card=' + enc : base + '/card/' + enc
}
