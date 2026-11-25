from datetime import datetime, timezone
from matching import score_pair

def pair(a,b):
    base={"time":datetime.now(timezone.utc),"place":"Library","description":"Campus item"}
    return score_pair({**base,**a},{**base,**b})[0]
def test_expected_pair_bands():
    assert pair({"item":"Navy Bottle","colour":"Navy","brand":"Milton"},{"item":"Blue Water Flask","colour":"Blue","brand":"Milton"})>=80
    def plausible(a,b):
        from datetime import timedelta
        now=datetime.now(timezone.utc)
        return score_pair({"place":"Library","time":now-timedelta(hours=72),**a},{"place":"Computer Lab","time":now,**b})[0]
    assert 60<=plausible({"item":"White Charger","colour":"White","description":"USB-C adapter with two ports"},{"item":"White USB-C Adapter","colour":"White","description":"Wall plug with a folding pin"})<=79
    assert 60<=plausible({"item":"Grey Hoodie","colour":"Grey","description":"Fleece sweatshirt with a pocket"},{"item":"Grey Jacket","colour":"Grey","description":"Zip jacket found folded on a bench"})<=79
    base={"place":"Library"}
    weak=score_pair({**base,"item":"Red Notebook","colour":"Red","description":"Red notebook with lined pages","time":datetime.now(timezone.utc)-__import__('datetime').timedelta(days=10)}, {**base,"item":"Blue Notebook","colour":"Blue","description":"Blue notebook with a blank cover","time":datetime.now(timezone.utc)})[0]
    assert weak<=59
