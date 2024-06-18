import sqlite3
from threading import Lock

class DBHandler():
    """
    Classe para a manipulação do banco de dados
    """

    def __init__(self,tablename):
        """
        Construtor
        :param tablename: Nome da tabela (Nome da missão)
        """
        self._dbpath = 'db\\scada.db'
        self._tablename = tablename
        self._col_names = ["Altitude", 
                        "Latitude", 
                        "Longitude", 
                        "Principal_Paraquedas_Estabilizador",
                        "Redundancia_Paraquedas_Estabilizador",
                        "Principal_Paraquedas_Principal",
                        "Acelerometro_X",
                        "Acelerometro_Y",
                        "Acelerometro_Z",
                        "Giroscopio_Roll",
                        "Giroscopio_Pitch",
                        "Giroscopio_Yaw",
                        "Tensão",
                        "RSSI"
        ]
        

    def conect(self):
        self._con = sqlite3.connect(self._dbpath, check_same_thread = False)
        self._cursor = self._con.cursor()
        self._lock = Lock()
        self._createTable()

    def __del__(self):
        try:
            self._con.close()
        except:
            pass

    def _createTable(self):
        """
        Método que cria a tabela para armazenamento dos dados caso ela não exista
        """
        try:
            sql_str = f"""
            CREATE TABLE IF NOT EXISTS {self._tablename} (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                """
            for n in self._col_names:
                sql_str += f'{n} REAL,'
            
            sql_str = sql_str[:-1]
            sql_str += ');'
            self._lock.acquire()
            self._cursor.execute(sql_str)
            self._con.commit()            
        except Exception as e:
            print("Erro CreateTable: ",e.args)
        finally:
            self._lock.release()

    def insertData(self, data):
        """
        Método para a inserção de dados no banco de dados
        :param data: json ou dicionario contendo todos os dados para a inserção
        """
        try:
            self._lock.acquire()
            self._data = self._handleData(data)
            str_cols = ','.join(self._data.keys())
            str_values = '"' + '", "'.join(str(self._data[k]) for k in self._data.keys()) + '"'
            sql_str = f'INSERT INTO {self._tablename} ({str_cols}) VALUES ({str_values});'
            self._cursor.execute(sql_str)
            self._con.commit()            
        except Exception as e:
            print("Erro insertData: ",e.args())
            raise e
        finally:
            self._lock.release()


    def _handleData(self, data):
        """
        Método 
        """
        try:
            newData = {"timestamp" : data['timestamp'],
                        "Altitude" : data['Alt'], 
                        "Latitude" : data['Lat'], 
                        "Longitude" : data['Long'], 
                        "Principal_Paraquedas_Estabilizador" : data['PPE'],
                        "Redundancia_Paraquedas_Estabilizador" : data['Redundancia Paraquedas Estabilizador'],
                        "Principal_Paraquedas_Principal" : data['PPP'],
                        "Acelerometro_X" : data['Acel(x)'],
                        "Acelerometro_Y" : data['Acel(y)'],
                        "Acelerometro_Z" : data['Acel(z)'],
                        "Giroscopio_Roll"   : data['Gyro(x)'],
                        "Giroscopio_Pitch"  : data['Gyro(y)'],
                        "Giroscopio_Yaw"    : data['Gyro(z)'],
                        "Tensão"            : data['Voltage'],
                        "RSSI" : data['RSSI']}
        
            return newData
        except Exception as e:
            print("Falha ao tratar dados: ",e.args())


    def disconect(self):
        self._con.close()

    # def selectData(self, cols):
    #     """
    #     Método que realiza a busca no BD para utilizar nos relatorios automatizados
    #     """
    #     try:
    #         self._lock.acquire()

    #         self._cursor.execute(sql_str)
    #         self._con.commit()
    #         self._lock.release()
    #     except Exception as e:
    #         print("Erro: ",e.args())