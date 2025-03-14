import os
import time
import requests
import pandas as pd
import gdown
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict, Type, Optional
from abc import ABC, abstractmethod

# ---------------- PATRON OBSERVADOR ----------------
class DownloadObserver(ABC):
    """Interfaz para los observadores que recibirán notificaciones de eventos de descarga."""
    @abstractmethod
    def update(self, name: str, status: str) -> None:
        pass

class DownloadLogger(DownloadObserver):
    """Observador que registra el estado de las descargas."""
    def __init__(self) -> None:
        self.results = []

    def update(self, name: str, status: str) -> None:
        self.results.append({"Nombre": name, "Estado": status})

    def save_to_csv(self, folder: str) -> None:
        df = pd.DataFrame(self.results)
        csv_path = os.path.join(folder, "descargas_resultados.csv")
        df.to_csv(csv_path, index=False)
        print(f"Resultados guardados en {csv_path}")

# ---------------- PATRON ESTRATEGIA ----------------
class DownloadStrategy(ABC):
    """Clase base abstracta para estrategias de descarga."""
    @abstractmethod
    def download(self, name: str, link: str, folder: str) -> str:
        pass

class GoogleDriveDownloader(DownloadStrategy):
    """Estrategia para descargar archivos desde Google Drive."""
    def download(self, name: str, link: str, folder: str) -> str:
        try:
            file_id = link.split("/d/")[1].split("/")[0]
            download_url = f"https://drive.google.com/uc?id={file_id}"
            output = os.path.join(folder, f"{name}.pdf")
            print(f"Inicio de la descarga: {name}")
            gdown.download(download_url, output, quiet=False)
            print(f"Fin de la descarga: {output}")
            return "Exitoso"
        except Exception as e:
            print(f"Error al descargar {name}: {e}")
            return "Fallido"

# ---------------- PATRON FACTORIA SINGLETON ----------------
class DownloadStrategyFactory:
    """Factoría Singleton para manejar estrategias de descarga."""
    _instance = None

    def __new__(cls) -> "DownloadStrategyFactory":
        if cls._instance is None:
            cls._instance = super(DownloadStrategyFactory, cls).__new__(cls)
            cls._instance._strategies = {
                "drive.google.com": GoogleDriveDownloader,
            }
        return cls._instance

    def get_strategy(self, link: str) -> Optional[DownloadStrategy]:
        for source, strategy in self._strategies.items():
            if source in link:
                return strategy()
        return None

# ---------------- SCRAPER Y DESCARGA ----------------
def get_pdf_links(url: str) -> List[Tuple[str, str]]:
    """Obtiene los enlaces de descarga de los archivos PDF junto con sus nombres."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error al acceder a la página: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = []
    
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) > 2:
            name = tds[0].get_text(strip=True)  # Extrae el nombre desde la primera columna
            a_tag = tds[2].find('a', href=True)
            if a_tag:
                links.append((name, a_tag['href']))
    
    return links

def download_pdfs(links: List[Tuple[str, str]], folder: str = "pdfs", delay: int = 2) -> None:
    """Descarga los archivos PDF de los enlaces proporcionados y registra el estado."""
    os.makedirs(folder, exist_ok=True)
    factory = DownloadStrategyFactory()
    logger = DownloadLogger()
    
    for name, link in links:
        strategy = factory.get_strategy(link)
        status = "No soportado"
        if strategy:
            status = strategy.download(name, link, folder)
        
        logger.update(name, status)
        time.sleep(delay)
    
    logger.save_to_csv(folder)

def main() -> None:
    """Función principal que ejecuta el scraping y descarga PDFs."""
    url = "https://secretariadesalud.chubut.gov.ar/epidemiological_releases"
    links = get_pdf_links(url)
    
    if not links:
        print("No se encontraron enlaces de descarga.")
        return
    
    download_pdfs(links)
    print("Descarga completada.")

if __name__ == "__main__":
    main()
