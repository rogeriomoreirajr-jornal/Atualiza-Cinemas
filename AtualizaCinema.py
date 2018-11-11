# coding: latin-1

import requests
import requests.packages.chardet
from operator import attrgetter
import re
import urllib2
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from lxml import etree
from functools import reduce
from datetime import date, timedelta, datetime
import requests_cache
import unicodedata
import os
from time import sleep
import locale

os.chdir('\\\\172.20.0.45\\jornalismo novo\\# Rob\xf4s\Cinemas\# script')
os.environ["REQUESTS_CA_BUNDLE"] = r"cacert.pem"
s = requests.Session()
senha = open(u'\\\\172.20.0.45\\jornalismo novo\_Utilit\xe1rios\password.txt').read()
root = etree.Element("Root")
locale.setlocale(locale.LC_TIME, "ptb")

proxy = ({
    'http':'http://rogerio.moreira:{}@172.20.0.75:8080'.format(senha),
	'https':'https://rogerio.moreira:{}@172.20.0.75:8080'.format(senha)
	})



def view(): print etree.tostring(root, pretty_print = True)
def reset():
	global root
	root = etree.Element("Root")

def write(output):
	open(caminho, 'w').write(output)
	print "\n\nTudo certo. Abra os arquivos para atualizá-los."

def title_br(string):
	temp = re.sub(' D([aeiou]s?) ',r' d\1 ', string.title())
	temp = re.sub(' ([AEIOU]s?) ',r' \1 '.lower(), temp)
	return temp

def make_soup(url):
    html = s.get(url, proxies=proxy, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.111 Safari/537.36'})
    return BeautifulSoup(html.content, "lxml")

def strip_accents(s):
	s = ''.join(c for c in unicodedata.normalize('NFD', s)
		if unicodedata.category(c) != 'Mn')
	return re.sub('(^ | $)', '',s).lower()

def tag(string):
	string = re.sub('^ ','',string)
	string = re.sub(' $','',string)
	string = re.sub(' ','-',string.lower())
	return strip_accents(string)


"""
API do ingresso.com

"""


shoppings = {
	'cinemark':'Floripa Shopping',
	'cineshow': 'Beira-Mar Shopping',
	'cinesystem':'Shopping Iguatemi',
	'cinepolis':'Continente Shopping',
	'itaguacu':u'Shopping Itaguaçu',
	'via catarina':'Via Catarina'
}

class cinema_ingresso():
	def __init__(self, cinema):
		print 'Checando {}'.format(cinema)

		self.parent_xml = etree.SubElement(root, 'cinema')
		etree.SubElement(self.parent_xml, 'shopping').text = shoppings[cinema]

		self.rooms = None
		self.rooms1 = None

		self.cinema = cinema

		dias = [datetime.today()+timedelta(days=1)]
		if datetime.today().weekday()==4:
			dias.append(datetime.today()+timedelta(days=2))

		for dia in dias:
			if not self.rooms:
				self.rooms = {}
				output = self.rooms
			else:
				self.rooms1 = {}
				output = self.rooms1

			self.check(dia, output)

		if self.rooms1:
			self.weekend()

		self.to_xml()

	def weekend(self):
		rooms_ = {k:self.rooms[k] for k in self.rooms}
		self.rooms = {}

		for room in rooms_:
			self.rooms[room] = {}
			movies = rooms_[room]
			for movie in movies:
				h_sab = movies[movie]

				if movie in self.rooms1[room]:
					h_dom = self.rooms1[room][movie]
				else: h_dom = []

				on_sab = [el+'&#185;' for el in h_sab if el not in h_dom]
				on_dom = [el+'&#178;' for el in h_dom if el not in h_sab]
				both = [el for el in h_sab if el in h_dom]

				horarios = set(on_sab+on_dom+both)

				self.rooms[room][movie] = horarios


	def check(self, dia, output):
		self.type = 'ingresso'

		api = 'https://api-content.ingresso.com/v0//sessions/city/{cidade}/theater/{cinema}?partnership=&date='.format

		cinemas = {
			'cinemark':{'city':'68','id':'443'},
			'cineshow':{'city':'68','id':'1473'},
			'cinesystem':{'city':'68','id':'437'},
			'cinepolis':{'city':'153','id':'1038'},
		}


		attrs = cinemas[self.cinema]
		city = attrs['city']
		id_ = attrs['id']

		self.url = api(cidade=city, cinema=id_)
		self.soup = make_soup(self.url)

		self.json = json.loads(self.soup.text)

		json_ = self.json

		dia = dia.strftime(format='%Y-%m-%d')

		if dia in [el['date'] for el in self.json]:
			movies, =  [el['movies'] for el in self.json if el['date']==dia]
			if len(movies)>0:
				for movie in movies:
					in_title = movie['title']
					for room in movie['rooms']:
						sala = room['name']
						if not sala in output:
							output[sala] = {}

						for session in room['sessions']:
							horario = session['date']['hour']

							if '3D' in session['type']:
								title = in_title + ' 3D'
							else:
								title = in_title

							if 'Dublado' in session['type']:
								horario += 'D'

							if not title in output[sala].keys():
								output[sala][title]=[]

							output[sala][title].append(horario)

	def to_xml(self):
		for room in sorted(self.rooms):
			parent_room = etree.SubElement(self.parent_xml, 'room')

			if self.type == 'ingresso':
				room_nome = ' '.join([self.cinema.title(), room.split(' ')[1]])
			elif self.type == 'arcoplex':
				room_nome = ' '.join(['Arcoplex', room])

			etree.SubElement(parent_room, 'sala').text = room_nome
			for filme in self.rooms[room]:
				parent_filme = etree.SubElement(parent_room, 'filme')
				etree.SubElement(parent_filme, 'titulo').text = filme
				etree.SubElement(parent_filme, 'horarios').text = ', '.join(self.rooms[room][filme])


class cinema_arcoplex(cinema_ingresso):
	def check(self, dia, output):
		self.type = 'arcoplex'

		if datetime.today().weekday() == 2:
			self.check_back(dia, output)
		else:
			self.check_front(dia, output)


	def check_front(self, dia, output):
		dict_arcoplex = {
		'itaguacu':'http://arcoplex.com.br/filme/?lang=003',
		'via catarina':'http://arcoplex.com.br/filme/?lang=055'
		}

		self.url = dict_arcoplex[self.cinema]
		self.soup = make_soup(self.url)

		filmes = self.soup.findAll('div','lista-filmes-loop-content')

		for filme in filmes:
			global possibilidades, dia_, horarios
			title = filme.find('h2','titulo-sub').text.title()

			horarios = filme.find('table','horarios-filmes').findAll('tr')

			dia_ = dia.strftime(format='%d/%m/%Y')
			if_dia = re.compile(dia_).search
			possibilidades = [el for el in horarios if if_dia(el.td.text)]

			for sessao in possibilidades:
				sessoes = [el.text for el in sessao.findAll('td')]
				horario = sessoes[1].split(' ')
				sala = sessoes[2]
				sala = re.sub('.+ (\d)',r'\1', sala)

				if sessoes[3]=='DUB':
					horarios = [el+'D' for el in horarios]

				if sessoes[5]=='3D':
					title += ' 3D'

				if not sala in output:
					output[sala] = {}

				output[sala][title] = horario[1:]



	def check_back(self, dia, output):
		dict_arcoplex = {
		'itaguacu':'https://webcinearcoplex2.com/compra_ingresso_online/?filial=003',
		'via catarina':'https://webcinearcoplex2.com/compra_ingresso_online/?filial=055'
		}

		base = 'https://webcinearcoplex2.com'

		self.url = dict_arcoplex[self.cinema]
		self.soup = make_soup(self.url)

		filmes = self.soup.find('div',{'id':'tabpromo1'}).findAll('a')

		global filmes_checar
		filmes_checar = []

		for filme in filmes:
			url_filme = base+filme['href']

			global soup_filme, if_dia, dia_
			soup_filme = make_soup(url_filme)
			title_raw = soup_filme.find('h2','titulo-filme').text
			title, = re.search('\n +(.+) ?- ?\dD.\n', title_raw).groups().title()

			filmes_checar.append(title)

			if re.search('3D.\n', title_raw): title+=' 3D'
			if re.search('D\n', title_raw): dublado = True

			dia_ = dia.strftime(format='%d de %B').title().replace(' De ', ' de ')

			if_dia = re.compile(dia_).search

			possibilidades = [el for el in soup_filme.findAll('tr') if if_dia(el.text)]

			if len(possibilidades)>0:
				horarios_raw, = possibilidades

				for linha in horarios_raw.findAll('a','espacoleft-btn'):
					horario_raw = linha.find('span','btncenter-amarelo').text
					horario = re.sub(' (\d\d):(\d\d) ',r'\1h\2', horario_raw)
					if dublado:
						horario += 'D'

					sala, = re.search('sala=(\d+)', linha['href']).groups()

					if not sala in self.rooms:
						self.rooms[sala] = {}

					if not title in self.rooms[sala]:
						self.rooms[sala][title] = []

					self.rooms[sala][title].append(horario)


"""
Fazer a função do final de semana
	- Função para checar, usando list-comprehension
	- Aplicar ¹ e ²
"""




def debug():
	master(debug = True)

def write(filename=''):
   	output = etree.tostring(root, pretty_print = True)

	output = re.sub('(\d)\:(\d)',r'\1h\2',output)
##	output = re.sub('^, ','',output)

	filename='horarios'
	open('{}.xml'.format(filename), 'w').write(output)

	print "\n\nTudo certo. Abra os arquivos para atualizá-los."

	raw_input()

cinemas = ['cinemark','cineshow','cinesystem','cinepolis']

def master(debug = False):
	global self
	for cinema in cinemas:
		self = cinema_ingresso(cinema)

	self = cinema_arcoplex('itaguacu')
	self = cinema_arcoplex('via catarina')

##self = cinema_ingresso('cinemark')

##self = cinema_arcoplex('itaguacu')


if __name__ == '__main__':
	master()
	view()
	write()
	if datetime.today().weekday() == 2:
		print 'Cheque se estes filmes estão corretos: '+', '.join(filmes_checar)