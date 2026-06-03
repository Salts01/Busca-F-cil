import requests
import time
from bs4 import BeautifulSoup
import tkinter as tk
#from tkinter import tkk
import threading as thd
import queue
import json
import os

req=requests.Session()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


fila = queue.Queue()
lock_arquivo = thd.Lock()

arquivo_json = os.path.join(
    BASE_DIR,
    "dados.jsonl"
)

trf4='https://eproc-jur.trf4.jus.br/eproc2trf4/externo_controlador.php?acao=jurisprudencia@jurisprudencia/listar_resultados'
trf6='https://eproc-jur.trf6.jus.br/eproc/externo_controlador.php?acao=jurisprudencia@jurisprudencia/listar_resultados'

trf2 = "https://eproc.trf2.jus.br/eproc/externo_controlador.php?acao=jurisprudencia@jurisprudencia/listar_resultados"



TRIBUNAIS = {
    "TRF2": trf2,
    "TRF4": trf4,
    "TRF6": trf6
}



def SalvarJson(processo, decisao):

    dado = {
        "processo": processo,
        "decisao": decisao
    }

    with lock_arquivo:
        with open(
            arquivo_json,
            "a",
            encoding="utf-8"
        ) as f:

            json.dump(
                dado,
                f,
                ensure_ascii=False
            )

            f.write("\n")


def ExtrairDecisao(item, tribunal):

    if tribunal == "TRF2":

        labels = item.find_all(
            "div",
            class_="resLabel"
        )

        for label in labels:

            if "DECISÃO" in label.get_text():

                valor = label.find_next(
                    "div",
                    class_="resValue"
                )

                if valor:
                    return valor.get_text(
                        " ",
                        strip=True
                    )

    else:

        decisao = item.find(
            "div",
            id=lambda x:
            x and
            "campo-completo" in x and
            "DECISÃO" in x
        )

        if decisao:

            return decisao.get_text(
                " ",
                strip=True
            )

    return None


def BuscaInformações(result,tribunal):

    for item in result:

        num_processo=item.find("a",class_='numero-processo')

        processo = (
            num_processo.get_text(strip=True)
            if num_processo
            else None       
                )
    

        decisao=ExtrairDecisao(item,tribunal)



        if processo and decisao:

            SalvarJson(processo, decisao)
            fila.put(processo)


def Pesquisa(texto_pesquisa,tribunal):
    
    url = TRIBUNAIS[tribunal]
    

    payload={
        "txtPesquisa":texto_pesquisa,
        "chkAgruparResultados":"on",
        "selOrigem[]":"1",
        "selTamanhoPagina":"100"
        }

    resp=req.post(url=url,data=payload)

    
    soup = BeautifulSoup(resp.text, "html.parser")

    Informações_gerais = soup.find_all(
    'div',
    class_='resultadoItem'
    )


    BuscaInformações(
    Informações_gerais,
    tribunal)
    
    total_paginas = int(soup.find(id="hdnTotalPaginas")["value"])


    if total_paginas>1:
        
        for pagina in range(2,total_paginas+1):

            payload["hdnPaginaAtual"]=str(pagina)
            
            resp=req.post(url=url,data=payload)

            soup = BeautifulSoup(resp.text, "html.parser")

            Informações_gerais=soup.find_all('div',class_='resultadoItem')

            BuscaInformações(Informações_gerais,tribunal)

            time.sleep(1)




tela=tk.Tk()

tribunal_var = tk.StringVar(value="TRF4")

tela.title('Busca Fácil')

Top=tk.Frame(tela)
Top.pack(fill='x')

label_pesquisa=tk.Label(Top,text='Pesquisa no tribunal:')

label_pesquisa.pack(side="left",padx=5)

label_tribunal = tk.Label(
    Top,
    text="Tribunal:"
)

label_tribunal.pack(
    side="left",
    padx=5
)

opcoes = tk.OptionMenu(
    Top,
    tribunal_var,
    "TRF2",
    "TRF4",
    "TRF6"
)

opcoes.pack(
    side="left",
    padx=5
)

entrada_busca=tk.Entry(Top,font=('Arial',12))

entrada_busca.pack(side="left",fill='x',expand=True,padx=5,pady=5)


label_filtro=tk.Label(Top,text='Filtro Local:')

label_filtro.pack(side="left",padx=5)

entrada_filtro=tk.Entry(Top,font=('Arial',12))
entrada_filtro.pack(side="left",padx=5)

botao_filtro = tk.Button(
    Top,
    text="Filtrar",
    command=lambda: Filtro(entrada_filtro.get())
)

botao_filtro.pack(side="left", padx=5)



tela.state('zoomed')
tela.resizable(True,True)
tela.minsize(1000,600)

principal=tk.PanedWindow(tela)
principal.pack(expand=True,fill="both")

lft=tk.Frame(principal)
rgt=tk.Frame(principal)

principal.add(lft)
principal.add(rgt)


frame_lista = tk.Frame(lft)

frame_lista.pack(
    expand=True,
    fill="both"
)

scroll_lista = tk.Scrollbar(
    frame_lista
)

scroll_lista.pack(
    side="right",
    fill="y"
)

lista = tk.Listbox(
    frame_lista,
    yscrollcommand=scroll_lista.set
)

lista.pack(
    side="left",
    expand=True,
    fill="both"
)

scroll_lista.config(
    command=lista.yview
)

texto=tk.Text(rgt)

texto.pack(expand=True,fill="both")



def UpdateScreen():
    while not fila.empty():
        processo=fila.get()
        lista.insert(tk.END,processo)

    tela.after(100,UpdateScreen)


def ShowDecisao(event):

    if not lista.curselection():
        return

    selected = lista.get(lista.curselection())

    decisao = ""

    
    with lock_arquivo:
        with open(
            arquivo_json,
            "r",
            encoding="utf-8"
        ) as f:

            for linha in f:

                try:
                     dado = json.loads(linha)

                except:
                    continue
                
                if dado["processo"] == selected:

                    decisao = dado["decisao"]

                    break

    texto.delete("1.0", tk.END)

    texto.insert(tk.END, decisao)

lista.bind("<<ListboxSelect>>",ShowDecisao)


def Filtro(texto_busca):

    lista.delete(0, tk.END)

    termos = texto_busca.lower().split()


    with lock_arquivo:
        with open(
            arquivo_json,
            "r",
            encoding="utf-8"
        ) as f:

            for linha in f:

                try:
                    dado = json.loads(linha)

                except:
                    continue

                conteudo = dado["decisao"].lower()

                if all(
                    termo in conteudo
                    for termo in termos
                ):

                    lista.insert(
                        tk.END,
                        dado["processo"]
                    )


def Iniciar():
    lista.delete(0,tk.END)
    tribunal=tribunal_var.get()
    open(arquivo_json, "w").close()

    termo=entrada_busca.get()  
    thd.Thread(
        target=Pesquisa,
        args=(termo,tribunal),
        daemon=True
    ).start()

botao_pesquisa=tk.Button(Top,text='Pesquisar',command=Iniciar)
botao_pesquisa.pack(side="left", padx=5)


UpdateScreen()


tela.mainloop()

