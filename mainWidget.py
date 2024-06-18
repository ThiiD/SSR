from kivy.uix.behaviors import button
import kivy
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
# from kivy.uix.image import AsyncImage
from kivy.core.window import Window
from popups import ConnectSocketPopup, ConnectSocketPopupError
from timeseriesgraph import TimeSeriesGraph
from kivy_garden.graph import LinePlot
from kivy_garden.mapview import MapMarkerPopup
from cliente import Cliente, UART
from threading import Thread, Lock
from time import sleep
from ipaddress import ip_address
from dbhandler import DBHandler

class MainWidget(FloatLayout):
    '''
    Widget principal do supervisório
    '''
    _updateWidgets = False
    _max_points = 1000
    _supernova_color = "#7D0101"
    _color_graphs = (1,0,0)
    _color_graphs_y = (0,1,0)
    _color_graphs_z = (0,0,1)

    def __init__(self, **kwargs):
        '''
        Construtor do widget principal
        '''
        super().__init__()
        self._porta = ""
        self._baudrate = ""
        self._missao = ""
        self._apogeu = 1
        self._serverIP = kwargs.get('server_ip')
        self._port = kwargs.get('server_port')
        self._conn = ConnectSocketPopup(self._serverIP, self._port)
        self._connError = ConnectSocketPopupError()
        self._updateDB = False
        self._lock = Lock
        
        #self._connect.start()
        Window.fullscreen = False
        Window.maximize()

        
        self._graphAltitude = self.DataGraph(self._max_points, self._color_graphs)
        self._graphAcelerometro = self.DataGraphAcel(self._max_points, self._color_graphs, self._color_graphs_y, self._color_graphs_z)
        self._graphGiroscopio = self.DataGraphGiro(self._max_points, self._color_graphs, self._color_graphs_y, self._color_graphs_z)
    pass

    def _startDataRead(self):
        """
        Método utilizado para configurar a conexão socket e inicializar uma thread para a leitura dos dados e atualização da interface grafica
        :param ip: ip da conexão socket
        :param port: porta para a conexao socket
        """
        try:
            self._apogeu = int(self._apogeu)
            self._porta = str(self._porta)
            self._baudrate = int(self._baudrate)         
            if True:
                Window.set_system_cursor("wait")
                # self._connect = Cliente(self._serverIP, self._port)
                self._connect = UART(self._porta, self._baudrate)
                self._connect.start()
                print("DEBUG 1")
                Window.set_system_cursor("arrow")
                self._updateThread = Thread(target = self.updater)
                self._updateThread.daemon = False
                self.ids.imagem_conexao.background_normal = 'imgs/conectado.png'
                self.ids.latitude.font_size = self.ids.altitude.font_size/2
                self.ids.longitude.font_size = self.ids.altitude.font_size/2
                self.ids.graphAcelerometro.clearLabel()
                self.ids.graphGiroscopio.clearLabel()
                self.ids.graphAltitude.clearLabel()
                self._dataBase = DBHandler(self._missao)
                self._disableNewConnections()
                self._limitesGraficos()
                self.enableSwitchesAndButtons()
                self._updateThread.start()  
                self._conn.dismiss()
            else:
                self._connError.ids.erroConnect.text = "Senha incorreta!"
                self._connError.open()
                raise Exception('Senha incorreta!')

        except ValueError:
            if (type(self._apogeu) != int):
                self._connError.ids.erroConnect.text = "Selecione o apogeu!"
                self._connError.open()
            else:
                self._connError.ids.erroConnect.text = "Erro: server/port mal definidos!"
                self._connError.open()

            raise ValueError

        except ConnectionRefusedError:
            Window.set_system_cursor("arrow")
            self._connError.ids.erroConnect.text = "Falha ao conectar!"
            self._connError.open()
            raise ConnectionRefusedError        

    
    def updater(self):
        """
        Metodo que invoca as rotinas de leitura de dados, utilizando a interface e inserção dos dados no banco de dados
        """
        while self._updateWidgets:
            try:    
                #Le dados
                self.readData()

                # Atualiza dados
                self._updateGUI()

                # Insere os dados no banco de dados
                if self._updateDB:
                    self._dataBase.insertData(data = self._instDados)
            except Exception as e:
                print(f'Erro updater: {e}')

    
    def readData(self):
        """
        Método para a leitura de dados via socket
        """
        try:
            # self._instDados = self._connect._method()
            self._instDados = self._connect.recieveData()
        except Exception as e:
            print(f'Falha ao adquirir os dados: {e}')
            raise e

    def _updateGUI(self):
        """
        Método para a atualização dos da interface gráfica
        """
        self.ids.altitude.text = str("{:.1f}".format(self._instDados['Alt']))
        self.ids.latitude.text = str("{:.15f}".format(self._instDados['Lat']))
        self.ids.longitude.text = str("{:.15f}".format(self._instDados['Long']))
        self.ids.acelerometroX.text = str("{:.2f}".format(self._instDados['Acel(x)']))
        self.ids.acelerometroY.text = str("{:.2f}".format(self._instDados['Acel(y)']))
        self.ids.acelerometroZ.text = str("{:.1f}".format(self._instDados['Acel(z)']))
        self.ids.giroscopioX.text = str(int(self._instDados['Gyro(x)']))
        self.ids.giroscopioY.text = str(int(self._instDados['Gyro(y)']))
        self.ids.giroscopioZ.text = str(int(self._instDados['Gyro(z)']))
        self.ids.RSSI.text = str(self._instDados['RSSI'])
        self.ids.voltage.text = str(self._instDados['Voltage'])
        self.ids.mapa.lat = self._instDados['Lat']
        self.ids.mapa.lon = self._instDados['Long']
        self.ids.mapaMarker.lat = self._instDados['Lat']
        self.ids.mapaMarker.lon = self._instDados['Long']
        self.ids.mapa.do_update(1)
        self.updateBoolean()
                                                   
        # Atualiza o grafico vertical de altitude
        self.ids.graficoMedidorAltitude.size_hint = (self.ids.medidorAltitude.size_hint[0], float(self._instDados['Alt']/(1.2*self._apogeu))*self.ids.medidorAltitude.size_hint[1]) if self._instDados['Alt'] <= 1.2*self._apogeu else (self.ids.medidorAltitude.size_hint[0], self.ids.medidorAltitude.size_hint[1])
        # self.ids.linhaGraficoMedidorAltitude.pos = (self.ids.medidorAltitude.pos[0], self.ids.medidorAltitude.pos[1] + float(self._instDados['Altitude']/36)*self.ids.medidorAltitude.size_hint[1])

        #Atualiza o grafico de linhas de altitude
        self.ids.graphAltitude.updateGraph((self._instDados['timestamp'], self._instDados['Alt']),0)

        # Atualiza o grafico com dados do acelerometro
        self.ids.graphAcelerometro.updateGraph((self._instDados['timestamp'], self._instDados['Acel(x)']), 0)
        self.ids.graphAcelerometro.updateGraph((self._instDados['timestamp'], self._instDados['Acel(y)']), 1)
        self.ids.graphAcelerometro.updateGraph((self._instDados['timestamp'], self._instDados['Acel(z)']), 2)
        
        # # Atualiza o grafico com dados do giroscopio
        self.ids.graphGiroscopio.updateGraph((self._instDados['timestamp'], self._instDados['Gyro(x)']), 0)
        self.ids.graphGiroscopio.updateGraph((self._instDados['timestamp'], self._instDados['Gyro(y)']), 1)
        self.ids.graphGiroscopio.updateGraph((self._instDados['timestamp'], self._instDados['Gyro(z)']), 2)

        

    
    def stopRefresh(self):
        """
        Método para parar de atualizar os widgets
        """
        self._updateWidgets = False


    def _limitesGraficos(self):
        """
        Método para definir os limites dos graficos e alterar a imagem da barra de altitude.
        """
        self.ids.graphAltitude.ymax = self._apogeu*1.2
        self.ids.graphAltitude.y_ticks_major = self._apogeu*1.2/6
        if self._apogeu == 500:
            self.ids.escala.source = 'imgs/escala500.png'
        if self._apogeu == 1000:
            self.ids.escala.source = 'imgs/escala1000.png'
        if self._apogeu == 3000:
            self.ids.escala.source = 'imgs/escala3000.png'
        if self._apogeu == 5000:
            self.ids.escala.source = 'imgs/escala5000.png'
        

    def DataGraph(self, xmax, plot_color, **kwargs):
        """
        Método para a criação do grafico de Altitude
        """
        # super().__init__(**kwargs)
        plot = LinePlot(line_width = 1.5, color = plot_color)
        self.ids.graphAltitude.add_plot(plot)
        self.ids.graphAltitude.xmax = xmax
            

    def DataGraphAcel(self, xmax, plot_color, plot_color_y, plot_color_z, **kwargs):
        """
        Método para a criação do grafico com dados do acelerometro.
        """
        plot = LinePlot(line_width = 1.5, color = plot_color)
        plot2 = LinePlot(line_width = 1.5, color = plot_color_y)
        plot3 = LinePlot(line_width = 1.5, color = plot_color_z)
        self.ids.graphAcelerometro.add_plot(plot)
        self.ids.graphAcelerometro.add_plot(plot2)
        self.ids.graphAcelerometro.add_plot(plot3)        
        self.ids.graphAcelerometro.xmax = xmax

    def DataGraphGiro(self, xmax, plot_color, plot_color_y, plot_color_z, **kwargs):
        """
        Método para a criação do grafico com dados do giroscopio.
        """
        plot = LinePlot(line_width = 1.5, color = plot_color)
        plot2 = LinePlot(line_width = 1.5, color = plot_color_y)
        plot3 = LinePlot(line_width = 1.5, color = plot_color_z)
        self.ids.graphGiroscopio.add_plot(plot)
        self.ids.graphGiroscopio.add_plot(plot2)
        self.ids.graphGiroscopio.add_plot(plot3)
        self.ids.graphGiroscopio.xmax = xmax
        


    def updateBoolean(self):
        """
        Método que atualiza os estados dos LED de acordo com o acionamento de cada paraquedas.
        """
        if self._instDados['PPE'] == 1:
            self.ids.paraquedasEstabilizadorPrincipal.source = 'imgs/green_led.png'
        
        if self._instDados['Redundancia Paraquedas Estabilizador'] == 1:
            self.ids.paraquedasEstabilizadorRedundante.source = 'imgs/green_led.png'

        if self._instDados['PPP'] == 1:
            self.ids.paraquedasPrincipal.source = 'imgs/green_led.png'

        if self._instDados['ready'] == 1:
            self.ids.ready_led.source = 'imgs/green_led.png'



    # Ativa todos os switches (torna todos os switches clicaveis)
    def enableSwitchesAndButtons(self):
        """
        Método para habilitar os switches após a conexão.
        """
        self.ids.bd_switch.disabled = False
        self.ids.bttnMarkBase.disabled = False


    # Métodos de callback para ativação de todos os switches
    def bdActivate(self, switchObject, switchValue):
        """
            Método para demonstração do estado de gravação dos dados em um Banco de Dados.
            Altera o valor de _updateDB, que diz se está ou não gravando os dados em um banco de dados. 
        """
        if switchValue:
            self.ids.bd_led.source = 'imgs/green_led.png'
            try:
                self._dataBase.conect()
            except Exception as e:
                print("Erro ao realizar a conexão com o banco de dados!")
        else:
            self.ids.bd_led.source = 'imgs/red_led.png'   
            self._dataBase.disconect()

        self._updateDB = switchValue


    def _markBase(self):
        """
        Método que cria um novo MapMarkerPopup para marcar a base de lançamento e desabilita o botão
        """
        marker = MapMarkerPopup(lat=self._instDados['Lat'], lon=self._instDados['Long'], source='imgs/markerBase.png')
        self.ids.mapa.add_widget(marker)
        self.ids.mapa.center_on(self._instDados['Lat'], self._instDados['Long'])
        self.ids.bttnMarkBase.disabled = True


    def _disableNewConnections(self):     
        """
        Método que trava os dados correspondentes a conexão
        """
        self._conn.ids.txt_porta.disabled = True
        self._conn.ids.txt_baudrate.disabled = True
        self._conn.ids.txt_missao.disabled = True
        self._conn.ids.txt_apogeu.disabled = True
        self._conn.ids.connButton.text = 'Desconectar'

    def _disconect(self):
        """
        Método para tratar a desconexão do supervisorio ao foguete.
        Reseta todas as configurações ao original.
        """
        self._conn.ids.txt_ip.disabled = False
        self._conn.ids.txt_port.disabled = False
        self._conn.ids.txt_login.disabled = False
        self._conn.ids.txt_senha.disabled = False
        self._conn.ids.txt_missao.disabled = False
        self._conn.ids.txt_apogeu.disabled = False
        self._conn.ids.connButton.text = 'Conectar'        
        self.ids.imagem_conexao.disabled = True
        self.ids.imagem_conexao.background_disabled_normal = 'imgs/desconectado.png'
        self._connect.disconect()
        self.ids.altitude.text = '-.-'
        self.ids.latitude.text = '-.-'
        self.ids.latitude.font_size = self.ids.altitude.font_size
        self.ids.longitude.text = '-.-'
        self.ids.longitude.font_size = self.ids.altitude.font_size
        self.ids.acelerometroX.text = '-.-'
        self.ids.acelerometroY.text = '-.-'
        self.ids.acelerometroZ.text = '-.-'
        self.ids.giroscopioX.text = '-.-'
        self.ids.giroscopioY.text = '-.-'
        self.ids.giroscopioZ.text = '-.-'
        self.ids.RSSI.text = '-.-'
        self.ids.mapa.lat = -21.778570807566982
        self.ids.mapa.lon = -43.373106180550764
        self.ids.mapaMarker.lat = -21.778570807566982
        self.ids.mapaMarker.lon = -43.373106180550764
        self.ids.mapa.do_update(1)
        self.ids.paraquedasEstabilizadorPrincipal.source = 'imgs/red_led.png'
        self.ids.paraquedasEstabilizadorRedundante.source = 'imgs/red_led.png'
        self.ids.paraquedasPrincipal.source = 'imgs/red_led.png'
        self.ids.bd_switch.active = False
        self.ids.bd_switch.disabled = True
        self.ids.bttnMarkBase.disabled = True
        self.ids.escala.source = 'imgs/escalaZerada.png'
        self.ids.graficoMedidorAltitude.size_hint = self.ids.medidorAltitude.size_hint[0], 0
        self.ids.graphAltitude.clearPlots()
        self.ids.graphAltitude.clearLabel()
        self.ids.graphAcelerometro.clearPlots()
        self.ids.graphAcelerometro.clearLabel()
        self.ids.graphGiroscopio.clearPlots()
        self.ids.graphGiroscopio.clearLabel()
        self._conn.dismiss()
        #self._updateThread.terminate() 

    def clickConnection(self):
        """
        Método que verifica se está sendo feita a conexão ou desconexão e chama o método correspondente.
        """
        self._updateWidgets = not self._updateWidgets
        try:
            if self._updateWidgets:
                self._startDataRead()
            else:
                self._disconect()                
        except:
            self._updateWidgets = not self._updateWidgets
            print('Falha ao conectar! _updateWidgets não alterado.')

