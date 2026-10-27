"""Maps whatever headers a raw download happens to use onto one schema.

Agmarknet, CEDA and data.gov.in all export the same fields under different
names ("Modal Price (Rs./Quintal)", "Modal_x0020_Price", "modal_price",
"Model Price"). Normalising here means no other module has to know or care
which source the file came from.

If scripts/inspect_data.py reports an unmapped column you need, add its
normalised spelling to the matching alias set below. This is the only file
you should ever need to edit for a new data source.
"""
import re

CANONICAL_COLUMNS = [
    "state", "district", "market", "commodity", "variety", "grade",
    "date", "min_price", "max_price", "modal_price", "arrivals",
]

# Columns the pipeline cannot run without.
REQUIRED_COLUMNS = ["market", "commodity", "date", "modal_price"]

COLUMN_ALIASES = {
    "state": {"state", "statename"},
    "district": {"district", "districtname", "dist"},
    # data.gov.in's Consumer Affairs price files call the market a "Centre"
    "market": {"market", "marketname", "mandi", "mandiname", "apmc", "apmcname",
               "centre", "centrename", "center", "centername"},
    "commodity": {"commodity", "commodityname", "crop", "cropname", "item"},
    "variety": {"variety", "varietyname"},
    "grade": {"grade", "gradename"},
    "date": {
        "date", "arrivaldate", "pricedate", "reporteddate", "reportdate",
        "dateofpricing", "day", "priceon",
    },
    "min_price": {"minprice", "minimumprice", "min", "minpricers", "pricemin"},
    "max_price": {"maxprice", "maximumprice", "max", "maxpricers", "pricemax"},
    # "Model Price" is a very common Agmarknet spelling of Modal Price.
    # A bare "Price" column (single-price sources) is treated as the modal price.
    # Files that carry min/max/modal separately normalise to minprice/maxprice/
    # modalprice, so there is no collision.
    "modal_price": {
        "modalprice", "modelprice", "modal", "model", "averageprice",
        "avgprice", "modalpricers", "pricemodal",
        "price", "wholesaleprice", "retailprice",
    },
    "arrivals": {
        "arrivals", "arrival", "arrivalquantity", "arrivalsintonnes",
        "arrivalstonnes", "quantity", "qty", "arrivalsqtl", "tonnes",
    },
}


def normalise_key(name) -> str:
    """Reduce a header to a comparable key.

    "Modal Price (Rs./Quintal)" -> "modalprice"
    "Modal_x0020_Price"         -> "modalprice"
    "Arrival_Date"              -> "arrivaldate"
    """
    s = str(name).lower()
    s = s.replace("_x0020_", " ")          # data.gov.in encodes spaces this way
    s = re.sub(r"\(.*?\)", " ", s)          # drop "(Rs./Quintal)" etc.
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def build_rename_map(columns):
    """Return (rename_map, unmapped_columns) for a raw DataFrame's columns."""
    lookup = {}
    for canon, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            lookup[alias] = canon

    rename, unmapped, claimed = {}, [], set()
    for col in columns:
        canon = lookup.get(normalise_key(col))
        if canon is None:
            unmapped.append(col)
        elif canon in claimed:
            # Two source columns map to the same field; keep the first.
            unmapped.append(col)
        else:
            rename[col] = canon
            claimed.add(canon)
    return rename, unmapped
