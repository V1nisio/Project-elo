"""Analisador de termos com spaCy: o módulo único que as etapas 2 e 3 vão reaproveitar.

Responsável: Belarmino Neto.

Cada texto passa pelo pipeline do modelo (tokenização, classe gramatical,
dependências, lematização, entidades) e por um componente nosso que põe o lema
em minúsculas. Depois, quatro detectores marcam as categorias do documento:
  1. PhraseMatcher por LEMMA: os termos de cada categoria, já lematizados;
  2. PhraseMatcher por LOWER: a forma literal, para o que o lematizador erra
     ("cota" vira "coto", "trava" vira "trar", "sandboxes" vira "sandboxe");
  3. Matcher com padrões de token: construções como "sem erro", "não confirmou";
  4. sinais das expressões regulares (padroes.py): 429, DUPLICATE_VALUE...
"""
import pandas as pd
import spacy
from spacy.language import Language
from spacy.matcher import Matcher, PhraseMatcher

from .categorias import CATEGORIAS, PADROES_TOKEN
from .padroes import MASCARAS, extrair, sinais_de_categoria

MODELOS = {"en": "en_core_web_sm", "pt": "pt_core_news_sm"}
CLASSES_UTEIS = {"NOUN", "PROPN", "VERB", "ADJ"}
PESSOA = {"PER", "PERSON"}
LIMITE_CARACTERES = 20_000          # uma thread enorme não pode travar o lote inteiro
MARCADORES = [marcador for _, _, marcador in MASCARAS] + ["<ID_SF>"]


@Language.component("lema_minusculo")
def lema_minusculo(doc):
    """'Token' no começo da frase e 'token' no meio viram o mesmo lema."""
    for token in doc:
        token.lemma_ = token.lemma_.lower()
    return doc


class Analisador:
    def __init__(self, idioma):
        self.idioma = idioma
        self.nlp = spacy.load(MODELOS[idioma])
        self.nlp.add_pipe("lema_minusculo", last=True)
        for marcador in MARCADORES:          # <CPF> é um token só, não "<", "CPF", ">"
            self.nlp.tokenizer.add_special_case(marcador, [{"ORTH": marcador}])
        self.por_lema = PhraseMatcher(self.nlp.vocab, attr="LEMMA")
        self.por_forma = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self.regras = Matcher(self.nlp.vocab)
        for categoria, info in CATEGORIAS.items():
            termos = info[idioma]                # "=termo": só pela forma exata
            self.por_lema.add(categoria, list(self.nlp.pipe(t for t in termos if not t.startswith("="))))
            self.por_forma.add(categoria, [self.nlp.make_doc(t.lstrip("=")) for t in termos])
        for categoria, padroes in PADROES_TOKEN[idioma].items():
            self.regras.add(categoria, padroes)

    def casamentos(self, doc):
        """(categoria, mecanismo, início, fim) de cada termo ou construção encontrada."""
        for mecanismo, matcher in (("lema", self.por_lema), ("forma", self.por_forma), ("regra", self.regras)):
            for match_id, inicio, fim in matcher(doc):
                yield self.nlp.vocab.strings[match_id], mecanismo, inicio, fim

    def analisar(self, documentos, sem_nomes=False, lote=32):
        """Resume cada documento SEM guardar o texto: categorias, lemas, sintagmas, entidades.

        sem_nomes=True (corpus de campo) descarta nome próprio e pessoa de tudo o
        que sai daqui, e guarda das entidades só o rótulo.
        """
        textos = (d["prosa"][:LIMITE_CARACTERES] for d in documentos)
        for registro, doc in zip(documentos, self.nlp.pipe(textos, batch_size=lote)):
            achados = extrair(registro["prosa"] + "\n" + registro.get("codigo", ""))
            mecanismos = {}
            for categoria, mecanismo, _, _ in self.casamentos(doc):
                mecanismos.setdefault(categoria, set()).add(mecanismo)
            for categoria in sinais_de_categoria(achados):
                mecanismos.setdefault(categoria, set()).add("regex")
            yield {
                "id": registro["id"], "fonte": registro["fonte"], "data": registro.get("data"),
                "titulo": registro.get("titulo"), "url": registro.get("url"),
                "n_comentarios": registro.get("n_comentarios", 0),
                "categorias": sorted(mecanismos),
                "mecanismos": {c: sorted(m) for c, m in mecanismos.items()},
                "n_tokens": len(doc),
                "lemas": self.lemas(doc, sem_nomes),
                "sintagmas": self.sintagmas(doc, sem_nomes),
                "entidades": [(e.label_, "" if sem_nomes else e.text)
                              for e in doc.ents if not (sem_nomes and e.label_ in PESSOA)],
                "achados": achados,
            }

    @staticmethod
    def lemas(doc, sem_nomes):
        return [t.lemma_ for t in doc
                if t.is_alpha and not t.is_stop and len(t) > 2 and t.pos_ in CLASSES_UTEIS
                and not (sem_nomes and (t.pos_ == "PROPN" or t.ent_type_ in PESSOA))]

    @staticmethod
    def sintagmas(doc, sem_nomes):
        """Sintagmas nominais ("the access token", "a conta duplicada") reduzidos aos lemas
        de substantivo e adjetivo, de 2 a 4 palavras (o modelo em português às vezes
        estica o sintagma até o verbo)."""
        saida = []
        for chunk in doc.noun_chunks:
            if sem_nomes and any(t.pos_ == "PROPN" or t.ent_type_ in PESSOA for t in chunk):
                continue
            palavras = [t.lemma_ for t in chunk if t.is_alpha and not t.is_stop and t.pos_ in {"NOUN", "PROPN", "ADJ"}]
            if 2 <= len(palavras) <= 4:
                saida.append(" ".join(palavras))
        return saida

    def tabela(self, texto):
        """Token a token, para mostrar o pipeline funcionando na apresentação."""
        doc = self.nlp(texto)
        marca = {}
        for categoria, mecanismo, inicio, fim in self.casamentos(doc):
            for i in range(inicio, fim):
                marca.setdefault(i, {}).setdefault(categoria, []).append(mecanismo)
        return pd.DataFrame([{"token": t.text, "lema": t.lemma_, "classe": t.pos_, "dependência": t.dep_,
                              "entidade": t.ent_type_,
                              "categoria": " ".join(f"{c} ({'+'.join(m)})" for c, m in marca.get(t.i, {}).items())}
                             for t in doc])
