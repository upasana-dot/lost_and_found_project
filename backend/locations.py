"""Approximate outdoor pins traced from the user-provided GLA University map view."""
CAMPUS_CENTER=(27.60486,77.5970753)

# Approximate campus-area pins. Indoor rooms still need a manually verified floor plan.
LOCATIONS={
    "Library":(27.60486,77.5970753),
    "Canteen":(27.60505,77.59384),
    "Auditorium":(27.60572,77.59625),
    "Computer Lab":(27.60525,77.59654),
    "Sports Ground":(27.60377,77.59648),
    "Parking Area":(27.60530,77.59310),
    "Classroom":(27.60532,77.59740),
    "Seminar Hall":(27.60466,77.59808),
}

BUILDINGS={
    "AB-1":{"place":"Classroom","lat":27.60525,"lng":77.59654},
    "AB-5":{"place":"Classroom","lat":27.60532,"lng":77.59740},
    "Computer Science Block":{"place":"Computer Lab","lat":27.60525,"lng":77.59654},
    "Central Library":{"place":"Library","lat":27.60486,"lng":77.5970753},
    "Canteen":{"place":"Canteen","lat":27.60505,"lng":77.59384},
    "Auditorium":{"place":"Auditorium","lat":27.60572,"lng":77.59625},
}
