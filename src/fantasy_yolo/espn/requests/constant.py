FANTASY_BASE_ENDPOINT = 'https://lm-api-reads.fantasy.espn.com/apis/v3/games/'
NEWS_BASE_ENDPOINT = 'https://site.api.espn.com/apis/fantasy/v3/games/'
# fantasy-yolo: trimmed to football. Upstream mapped five sports; this copy
# ships only the football League, so listing the others would let a caller
# construct a request object for a sport that has no client behind it.
FANTASY_SPORTS = {
    'nfl': 'ffl',
}