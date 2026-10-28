"""Preset places: the 12 backtest locations plus provincial and flood-prone towns."""

PLACES = {
    "Lusaka (Kanyama)": (-15.445, 28.245),
    "Chongwe": (-15.330, 28.680),
    "Kafue": (-15.770, 28.180),
    "Mumbwa": (-14.980, 27.060),
    "Kabwe": (-14.450, 28.450),
    "Mazabuka": (-15.860, 27.750),
    "Monze": (-16.280, 27.480),
    "Namwala": (-15.750, 26.440),
    "Gwembe (Munyumbwe)": (-16.620, 27.730),
    "Choma": (-16.810, 26.980),
    "Livingstone": (-17.850, 25.860),
    "Mambwe (Malambo)": (-13.100, 31.800),
    "Lumezi": (-12.980, 32.700),
    "Lundazi": (-12.290, 33.180),
    "Lusangazi (Msanzala)": (-14.100, 31.400),
    "Chipata": (-13.630, 32.650),
    "Samfya": (-11.360, 29.550),
    "Mansa": (-11.200, 28.890),
    "Kasama": (-10.210, 31.180),
    "Kitwe": (-12.800, 28.210),
    "Ndola": (-12.970, 28.640),
    "Chingola": (-12.530, 27.850),
    "Solwezi": (-12.170, 26.390),
    "Mongu": (-15.250, 23.130),
    "Senanga": (-16.120, 23.270),
    "Lukulu": (-14.380, 23.240),
}


def find(name):
    """Case-insensitive lookup that also accepts the start of a name."""
    key = name.strip().lower()
    for k, v in PLACES.items():
        if k.lower() == key or k.lower().startswith(key):
            return k, v
    raise KeyError(f"Unknown place '{name}'. Known places: {', '.join(PLACES)}")
