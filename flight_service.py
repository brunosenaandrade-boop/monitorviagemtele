import os
from amadeus import Client, ResponseError
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FlightOffer:
    price: float
    currency: str
    departure_time: str
    arrival_time: str
    airline: str
    stops: int
    duration: str
    origin: str
    destination: str
    return_departure: Optional[str] = None
    return_arrival: Optional[str] = None


class FlightService:
    def __init__(self):
        self.amadeus = Client(
            client_id=os.getenv("AMADEUS_API_KEY"),
            client_secret=os.getenv("AMADEUS_API_SECRET"),
            hostname="test"  # Use "production" para produção
        )

    def search_flights(self, origin: str, destination: str, departure_date: str,
                       return_date: Optional[str] = None, adults: int = 1) -> list[FlightOffer]:
        """Busca voos disponíveis."""
        try:
            params = {
                "originLocationCode": origin.upper(),
                "destinationLocationCode": destination.upper(),
                "departureDate": departure_date,
                "adults": adults,
                "currencyCode": "BRL",
                "max": 5
            }

            if return_date:
                params["returnDate"] = return_date

            response = self.amadeus.shopping.flight_offers_search.get(**params)

            offers = []
            for offer in response.data:
                price = float(offer["price"]["total"])
                currency = offer["price"]["currency"]

                # Pegar detalhes do primeiro segmento (ida)
                first_segment = offer["itineraries"][0]["segments"][0]
                last_segment = offer["itineraries"][0]["segments"][-1]

                departure_time = first_segment["departure"]["at"]
                arrival_time = last_segment["arrival"]["at"]
                airline = first_segment["carrierCode"]
                stops = len(offer["itineraries"][0]["segments"]) - 1
                duration = offer["itineraries"][0]["duration"]

                # Dados da volta (se houver)
                return_departure = None
                return_arrival = None
                if len(offer["itineraries"]) > 1:
                    return_first = offer["itineraries"][1]["segments"][0]
                    return_last = offer["itineraries"][1]["segments"][-1]
                    return_departure = return_first["departure"]["at"]
                    return_arrival = return_last["arrival"]["at"]

                offers.append(FlightOffer(
                    price=price,
                    currency=currency,
                    departure_time=departure_time,
                    arrival_time=arrival_time,
                    airline=airline,
                    stops=stops,
                    duration=duration,
                    origin=origin.upper(),
                    destination=destination.upper(),
                    return_departure=return_departure,
                    return_arrival=return_arrival
                ))

            return sorted(offers, key=lambda x: x.price)

        except ResponseError as error:
            print(f"Erro na API Amadeus: {error}")
            return []

    def get_cheapest_price(self, origin: str, destination: str, departure_date: str,
                           return_date: Optional[str] = None, adults: int = 1) -> Optional[FlightOffer]:
        """Retorna o voo mais barato."""
        offers = self.search_flights(origin, destination, departure_date, return_date, adults)
        return offers[0] if offers else None

    def search_airports(self, keyword: str) -> list[dict]:
        """Busca aeroportos por nome ou código."""
        try:
            response = self.amadeus.reference_data.locations.get(
                keyword=keyword,
                subType="AIRPORT,CITY"
            )
            return [
                {
                    "code": loc["iataCode"],
                    "name": loc["name"],
                    "city": loc.get("address", {}).get("cityName", ""),
                    "country": loc.get("address", {}).get("countryName", "")
                }
                for loc in response.data[:5]
            ]
        except ResponseError as error:
            print(f"Erro ao buscar aeroportos: {error}")
            return []

    def format_flight_message(self, offer: FlightOffer) -> str:
        """Formata mensagem do voo para o Telegram."""
        dep_dt = datetime.fromisoformat(offer.departure_time.replace("Z", "+00:00"))
        arr_dt = datetime.fromisoformat(offer.arrival_time.replace("Z", "+00:00"))

        # Formatar duração (PT2H30M -> 2h30)
        duration = offer.duration.replace("PT", "").replace("H", "h").replace("M", "m")

        msg = f"""
✈️ *{offer.origin} → {offer.destination}*

💰 *Preço: R$ {offer.price:,.2f}*

📅 Ida: {dep_dt.strftime("%d/%m/%Y às %H:%M")}
🛬 Chegada: {arr_dt.strftime("%d/%m/%Y às %H:%M")}
⏱ Duração: {duration}
🛫 Companhia: {offer.airline}
🔄 Paradas: {offer.stops if offer.stops > 0 else "Direto"}
"""

        if offer.return_departure:
            ret_dep = datetime.fromisoformat(offer.return_departure.replace("Z", "+00:00"))
            ret_arr = datetime.fromisoformat(offer.return_arrival.replace("Z", "+00:00"))
            msg += f"""
📅 Volta: {ret_dep.strftime("%d/%m/%Y às %H:%M")}
🛬 Chegada: {ret_arr.strftime("%d/%m/%Y às %H:%M")}
"""

        return msg
