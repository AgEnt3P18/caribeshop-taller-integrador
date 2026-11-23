"""Pruebas de carga CaribeShop (P1/P2).

Modos (variable de entorno LOCUST_MODE):
  capacity  rampa lineal +USERS_STEP cada STEP_SECONDS (P1.1: buscar p95 > 1 s)
  staircase perfil escalonado subida / sostenida / bajada de 28 min (P1.2)
  steady    carga moderada constante (P2: pruebas de falla)

Ejemplo:
  LOCUST_MODE=staircase locust -f locustfile.py --host http://<fqdn> \
      --headless --csv ../evidencias/p1_staircase --html ../evidencias/p1_staircase.html
"""
import os

from locust import HttpUser, LoadTestShape, between, task

MODE = os.getenv("LOCUST_MODE", "staircase")


class Shopper(HttpUser):
    wait_time = between(0.5, 1.5)

    @task(8)
    def browse(self):
        self.client.get("/work", name="/work")

    @task(1)
    def home(self):
        self.client.get("/", name="/")


class CapacityShape(LoadTestShape):
    step_users = int(os.getenv("USERS_STEP", "5"))
    step_seconds = int(os.getenv("STEP_SECONDS", "60"))
    max_users = int(os.getenv("MAX_USERS", "120"))

    def tick(self):
        t = self.get_run_time()
        users = (int(t // self.step_seconds) + 1) * self.step_users
        if users > self.max_users:
            return None
        return users, self.step_users


class StaircaseShape(LoadTestShape):
    # (fin_en_segundos, usuarios). Total 28 min.
    stages = [
        (180, 10),     # 0-3   calentamiento
        (360, 30),     # 3-6   subida
        (540, 50),     # 6-9   subida
        (1080, 70),    # 9-18  carga sostenida (debe disparar scale-out)
        (1260, 30),    # 18-21 bajada
        (1680, 5),     # 21-28 valle (debe disparar scale-in)
    ]

    def tick(self):
        t = self.get_run_time()
        for end, users in self.stages:
            if t < end:
                return users, 10
        return None


class SteadyShape(LoadTestShape):
    users = int(os.getenv("STEADY_USERS", "20"))
    duration = int(os.getenv("DURATION", "600"))

    def tick(self):
        if self.get_run_time() > self.duration:
            return None
        return self.users, 10


# Locust usa la primera subclase de LoadTestShape definida a nivel de modulo;
# se eliminan las que no aplican al modo elegido.
_shapes = {"capacity": CapacityShape, "staircase": StaircaseShape, "steady": SteadyShape}
for _name, _cls in list(_shapes.items()):
    if _name != MODE:
        del globals()[_cls.__name__]
del _shapes, _name, _cls
