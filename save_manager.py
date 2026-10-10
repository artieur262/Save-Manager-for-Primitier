"""
Gestionnaire de sauvegardes Primitier.

Le jeu n'a que 9 slots (save1.dat ... save9.dat). Ce script permet de :
- voir le contenu des 9 slots (seed, mode, date) ;
- donner un nom à un monde : un dossier Mondes/<nom>/ est créé, avec un
  fichier seed.txt qui contient la seed du monde ;
- déplacer une save d'un slot vers le dossier de son monde (libère le slot) ;
- recopier une save rangée vers un slot pour y rejouer ;
- supprimer une save (slot ou save rangée), envoyée à la corbeille Windows.

Un monde est reconnu par sa seed : une save va toujours dans le dossier du
monde qui a la même seed, impossible de la ranger dans le mauvais monde.
"""
import ctypes
import gzip
import os
import re
import shutil
import time
import tkinter as tk
from ctypes import wintypes
from tkinter import font as tkfont
from tkinter import messagebox, simpledialog, ttk
from typing import Dict, List, Optional

DOSSIER_SAVES = os.path.dirname(os.path.abspath(__file__))
DOSSIER_MONDES = os.path.join(DOSSIER_SAVES, "Mondes")
NOMBRE_SLOTS = 8
FICHIER_SEED = "seed.txt"

# Mode VR : tout est grossi pour être lisible et cliquable dans le casque.
ECHELLE_VR = 1.75
LARGEUR_DEFILEMENT_VR = 40
POLICES = ("TkDefaultFont", "TkTextFont", "TkHeadingFont")

CARACTERES_INTERDITS = '\\/:*?"<>|'
NOMS_RESERVES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefixe}{i}" for prefixe in ("COM", "LPT") for i in range(1, 10)
}


# --------------------------------------------------------------------------
# Lecture des saves
# --------------------------------------------------------------------------

def chemin_slot(numero: int) -> str:
    return os.path.join(DOSSIER_SAVES, f"save{numero}.dat")


def lire_infos_save(chemin: str) -> Optional[Dict]:
    """Lit la seed et le mode d'une save (JSON gzippé, infos au tout début)."""
    try:
        with gzip.open(chemin, "rb") as fichier:
            debut = fichier.read(600).decode("utf-8", errors="replace")
    except (OSError, EOFError):
        return None
    seed = re.search(r'"seed":(-?\d+)', debut)
    if seed is None:
        return None
    creatif = re.search(r'"isCreativeMode":(true|false)', debut)
    return {
        "seed": int(seed.group(1)),
        "creatif": creatif is not None and creatif.group(1) == "true",
    }


def formater_date(chemin: str, pour_fichier: bool = False) -> str:
    modele = "%Y-%m-%d_%Hh%M" if pour_fichier else "%d/%m/%Y %H:%M"
    return time.strftime(modele, time.localtime(os.path.getmtime(chemin)))


def formater_taille(chemin: str) -> str:
    return f"{os.path.getsize(chemin) / 1_000_000:.1f} Mo"


def lister_slots() -> List[Dict]:
    """Etat des 9 slots. "infos" vaut None si le slot est vide ou illisible."""
    slots = []
    for numero in range(1, NOMBRE_SLOTS + 1):
        chemin = chemin_slot(numero)
        existe = os.path.isfile(chemin)
        slots.append({
            "numero": numero,
            "chemin": chemin,
            "existe": existe,
            "infos": lire_infos_save(chemin) if existe else None,
        })
    return slots


# --------------------------------------------------------------------------
# Mondes
# --------------------------------------------------------------------------

def lister_mondes() -> Dict[int, str]:
    """Renvoie {seed: dossier du monde} pour tous les mondes nommés."""
    mondes = {}
    if not os.path.isdir(DOSSIER_MONDES):
        return mondes
    for nom in sorted(os.listdir(DOSSIER_MONDES)):
        dossier = os.path.join(DOSSIER_MONDES, nom)
        try:
            with open(os.path.join(dossier, FICHIER_SEED), encoding="utf-8") as fichier:
                mondes[int(fichier.read().strip())] = dossier
        except (OSError, ValueError):
            continue
    return mondes


def lister_saves_monde(dossier: str) -> List[str]:
    return sorted(
        os.path.join(dossier, nom)
        for nom in os.listdir(dossier)
        if nom.lower().endswith(".dat")
    )


def verifier_nom(nom: str) -> str:
    """Nettoie le nom et lève ValueError s'il ne peut pas servir de dossier."""
    nom = nom.strip().rstrip(".")
    if not nom:
        raise ValueError("Le nom ne peut pas être vide.")
    if any(c in CARACTERES_INTERDITS or ord(c) < 32 for c in nom):
        raise ValueError(f"Le nom ne peut pas contenir : {CARACTERES_INTERDITS}")
    if nom.upper() in NOMS_RESERVES:
        raise ValueError(f"« {nom} » est un nom réservé par Windows.")
    return nom


def nommer_monde(seed: int, nom: str) -> str:
    """Crée le dossier du monde, ou le renomme si ce monde a déjà un nom."""
    nom = verifier_nom(nom)
    nouveau = os.path.join(DOSSIER_MONDES, nom)
    ancien = lister_mondes().get(seed)

    if ancien is not None and os.path.normcase(ancien) == os.path.normcase(nouveau):
        if ancien != nouveau:
            os.rename(ancien, nouveau)
        return nouveau
    if os.path.exists(nouveau):
        raise ValueError(f"Un autre monde s'appelle déjà « {nom} ».")

    if ancien is not None:
        os.rename(ancien, nouveau)
    else:
        os.makedirs(nouveau)
        with open(os.path.join(nouveau, FICHIER_SEED), "w", encoding="utf-8") as fichier:
            fichier.write(str(seed))
    return nouveau


def deplacer_slot_vers_monde(numero: int) -> str:
    """Déplace saveN.dat dans le dossier de son monde. Renvoie le nouveau chemin."""
    source = chemin_slot(numero)
    infos = lire_infos_save(source)
    if infos is None:
        raise ValueError(f"Le slot {numero} est vide ou illisible.")
    dossier = lister_mondes().get(infos["seed"])
    if dossier is None:
        raise LookupError("Ce monde n'a pas encore de nom.")

    base = f"save_{formater_date(source, pour_fichier=True)}"
    destination = os.path.join(dossier, base + ".dat")
    compteur = 2
    while os.path.exists(destination):
        destination = os.path.join(dossier, f"{base}_{compteur}.dat")
        compteur += 1
    shutil.move(source, destination)
    return destination


def copier_vers_slot(chemin_save: str, numero: int, ecraser: bool = False) -> None:
    """Copie une save rangée vers un slot (la save rangée reste dans le monde)."""
    destination = chemin_slot(numero)
    if os.path.exists(destination) and not ecraser:
        raise FileExistsError(f"Le slot {numero} est déjà occupé.")
    shutil.copy2(chemin_save, destination)


class _SHFILEOPSTRUCTW(ctypes.Structure):
    if ctypes.sizeof(ctypes.c_void_p) == 4:
        _pack_ = 1
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", wintypes.WORD),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def supprimer_save(chemin: str) -> None:
    """Envoie une save à la corbeille Windows (récupérable en cas d'erreur)."""
    if not os.path.isfile(chemin):
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")
    # pFrom doit finir par deux caractères nuls : un ici, un ajouté par le buffer.
    source = ctypes.create_unicode_buffer(os.path.abspath(chemin) + "\0")
    operation = _SHFILEOPSTRUCTW()
    operation.wFunc = 3  # FO_DELETE
    operation.pFrom = ctypes.cast(source, wintypes.LPCWSTR)
    # FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI
    operation.fFlags = 0x0004 | 0x0010 | 0x0040 | 0x0400
    code = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    if code != 0 or operation.fAnyOperationsAborted or os.path.exists(chemin):
        raise OSError(f"Impossible d'envoyer à la corbeille : {os.path.basename(chemin)}")


# --------------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------------

class GestionnaireSaves(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Sauvegardes Primitier")

        self.slots = []  # type: List[Dict]
        self.mondes = {}  # type: Dict[int, str]

        # Le mode VR agrandit ces polices ; on garde leur taille d'origine.
        self.tailles_polices = {
            nom: tkfont.nametofont(nom).cget("size") for nom in POLICES
        }
        self.style = ttk.Style(self)
        self.marge_bouton = self.style.lookup("TButton", "padding")
        self.mode_vr = tk.BooleanVar(self, value=False)

        self._construire()
        self.actualiser()
        self.appliquer_mode_vr()

    def _construire(self) -> None:
        barre = ttk.Frame(self)
        barre.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))
        ttk.Checkbutton(
            barre, text="Mode VR", style="Toolbutton", variable=self.mode_vr,
            command=self.appliquer_mode_vr,
        ).pack(side="right")

        # Slots à gauche, mondes à droite.
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(1, weight=1)

        # --- Slots du jeu ---
        self.cadre_slots = ttk.LabelFrame(self, text="Slots du jeu", padding=8)
        self.cadre_slots.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)
        self.cadre_slots.rowconfigure(0, weight=1)
        self.cadre_slots.columnconfigure(0, weight=1)

        self.colonnes_slots = (
            ("slot", "Slot", 45),
            ("monde", "Monde", 150),
            ("seed", "Seed", 100),
            ("mode", "Mode", 65),
            ("date", "Date", 115),
            ("taille", "Taille", 65),
        )
        self.arbre_slots = ttk.Treeview(
            self.cadre_slots, columns=[c[0] for c in self.colonnes_slots],
            show="headings", selectmode="browse", height=NOMBRE_SLOTS,
        )
        for identifiant, titre, _ in self.colonnes_slots:
            self.arbre_slots.heading(identifiant, text=titre)
            self.arbre_slots.column(identifiant, anchor="w")
        self.arbre_slots.tag_configure("vide", foreground="gray")
        self.arbre_slots.grid(row=0, column=0, sticky="nsew")
        self.arbre_slots.bind("<Double-1>", lambda _: self.deplacer_selection())
        self.defilement_slots = self._creer_defilement(self.cadre_slots, self.arbre_slots)

        self.cadre_boutons_slots = ttk.Frame(self.cadre_slots)
        self.cadre_boutons_slots.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.boutons_slots = [
            ttk.Button(self.cadre_boutons_slots, text="Nommer ce monde",
                       command=self.nommer_selection),
            ttk.Button(self.cadre_boutons_slots, text="Déplacer dans son monde  →",
                       command=self.deplacer_selection),
            ttk.Button(self.cadre_boutons_slots, text="Supprimer",
                       command=self.supprimer_slot),
            ttk.Button(self.cadre_boutons_slots, text="Actualiser",
                       command=self.actualiser),
        ]

        # --- Mondes ---
        self.cadre_mondes = ttk.LabelFrame(self, text="Mes mondes", padding=8)
        self.cadre_mondes.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)
        self.cadre_mondes.rowconfigure(0, weight=1)
        self.cadre_mondes.columnconfigure(0, weight=1)

        self.colonnes_mondes = (
            ("#0", "Monde / save", 250),
            ("detail", "Seed / mode", 100),
            ("taille", "Taille", 65),
        )
        self.arbre_mondes = ttk.Treeview(
            self.cadre_mondes, columns=("detail", "taille"), selectmode="browse",
        )
        for identifiant, titre, _ in self.colonnes_mondes:
            self.arbre_mondes.heading(identifiant, text=titre)
        self.arbre_mondes.grid(row=0, column=0, sticky="nsew")
        self.defilement_mondes = self._creer_defilement(self.cadre_mondes, self.arbre_mondes)

        self.cadre_boutons_mondes = ttk.Frame(self.cadre_mondes)
        self.cadre_boutons_mondes.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.boutons_mondes = [
            ttk.Button(self.cadre_boutons_mondes, text="←  Copier vers un slot",
                       command=self.copier_selection),
            ttk.Button(self.cadre_boutons_mondes, text="Renommer",
                       command=self.renommer_monde),
            ttk.Button(self.cadre_boutons_mondes, text="Supprimer",
                       command=self.supprimer_save_monde),
            ttk.Button(self.cadre_boutons_mondes, text="Ouvrir le dossier",
                       command=self.ouvrir_dossier),
        ]

    @staticmethod
    def _creer_defilement(cadre: ttk.LabelFrame, arbre: ttk.Treeview) -> tk.Scrollbar:
        """Barre de défilement large, affichée seulement en mode VR."""
        barre = tk.Scrollbar(
            cadre, orient="vertical", command=arbre.yview, width=LARGEUR_DEFILEMENT_VR)
        arbre.configure(yscrollcommand=barre.set)
        barre.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        return barre

    # --- Mode VR ---

    def _echelle_vr(self) -> float:
        """Grossissement du mode VR, réduit si l'écran est trop étroit."""
        return max(1.2, min(ECHELLE_VR, (self.winfo_screenwidth() - 172) / 652))

    def appliquer_mode_vr(self) -> None:
        """Règle polices, boutons, barres de défilement et fenêtre selon le mode."""
        vr = self.mode_vr.get()
        echelle = self._echelle_vr() if vr else 1.0

        for nom, taille in self.tailles_polices.items():
            tkfont.nametofont(nom).configure(size=int(round(taille * echelle)))
        hauteur_texte = tkfont.nametofont("TkDefaultFont").metrics("linespace")
        self.style.configure("Treeview", rowheight=hauteur_texte + (10 if vr else 5))
        for nom_style in ("TButton", "Toolbutton"):
            self.style.configure(nom_style, padding=12 if vr else self.marge_bouton)

        # Les colonnes grossissent moins que le texte si les deux panneaux,
        # côte à côte, ne tiendraient pas dans la largeur de l'écran.
        echelle_colonnes = echelle
        if vr:
            largeur_base = sum(c[2] for c in self.colonnes_slots + self.colonnes_mondes)
            place = self.winfo_screenwidth() - 2 * LARGEUR_DEFILEMENT_VR - 90
            echelle_colonnes = min(echelle, place / largeur_base)
        for arbre, colonnes in ((self.arbre_slots, self.colonnes_slots),
                                (self.arbre_mondes, self.colonnes_mondes)):
            for identifiant, _, largeur in colonnes:
                arbre.column(identifiant, width=int(largeur * echelle_colonnes))

        for barre in (self.defilement_slots, self.defilement_mondes):
            if vr:
                barre.grid()
            else:
                barre.grid_remove()

        self._placer_boutons(self.cadre_boutons_slots, self.boutons_slots, vr)
        self._placer_boutons(self.cadre_boutons_mondes, self.boutons_mondes, vr)

        self.minsize(1, 1)
        if vr:
            self.state("zoomed")
        else:
            self.state("normal")
            # Taille calculée d'après le contenu, pour qu'aucun bouton ne soit coupé.
            self.geometry("")
            self.update_idletasks()
            self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())

    @staticmethod
    def _placer_boutons(cadre: ttk.Frame, boutons: List[ttk.Button], vr: bool) -> None:
        """VR : gros boutons de même largeur, deux par ligne. Sinon : sur une
        ligne, serrés à gauche, le dernier à droite."""
        for colonne in range(len(boutons) + 1):
            cadre.columnconfigure(colonne, weight=0, uniform="")
        if vr:
            for indice, bouton in enumerate(boutons):
                bouton.grid(row=indice // 2, column=indice % 2, sticky="ew",
                            padx=4, pady=4)
            for colonne in range(2):
                cadre.columnconfigure(colonne, weight=1, uniform="boutons")
        else:
            dernier = len(boutons) - 1
            for colonne, bouton in enumerate(boutons[:dernier]):
                bouton.grid(row=0, column=colonne, sticky="", padx=(0, 6), pady=0)
            cadre.columnconfigure(dernier, weight=1)
            boutons[dernier].grid(row=0, column=dernier + 1, sticky="e", padx=0, pady=0)

    # --- Affichage ---

    def actualiser(self) -> None:
        self.slots = lister_slots()
        self.mondes = lister_mondes()

        self.arbre_slots.delete(*self.arbre_slots.get_children())
        for slot in self.slots:
            numero, infos = slot["numero"], slot["infos"]
            if not slot["existe"]:
                valeurs = (numero, "(vide)", "", "", "", "")
            elif infos is None:
                valeurs = (numero, "(illisible)", "", "",
                           formater_date(slot["chemin"]), formater_taille(slot["chemin"]))
            else:
                dossier = self.mondes.get(infos["seed"])
                valeurs = (
                    numero,
                    os.path.basename(dossier) if dossier else "(sans nom)",
                    infos["seed"],
                    "Créatif" if infos["creatif"] else "Survie",
                    formater_date(slot["chemin"]),
                    formater_taille(slot["chemin"]),
                )
            self.arbre_slots.insert(
                "", "end", iid=str(numero), values=valeurs,
                tags=() if infos else ("vide",),
            )

        self.arbre_mondes.delete(*self.arbre_mondes.get_children())
        for seed, dossier in sorted(self.mondes.items(), key=lambda m: m[1].lower()):
            self.arbre_mondes.insert(
                "", "end", iid=dossier, text=os.path.basename(dossier),
                values=(seed, ""), open=True,
            )
            for chemin in lister_saves_monde(dossier):
                infos = lire_infos_save(chemin)
                if infos is None:
                    mode = "illisible"
                else:
                    mode = "Créatif" if infos["creatif"] else "Survie"
                self.arbre_mondes.insert(
                    dossier, "end", iid=chemin, text=os.path.basename(chemin),
                    values=(mode, formater_taille(chemin)),
                )

    def _slot_selectionne(self) -> Optional[Dict]:
        selection = self.arbre_slots.selection()
        if not selection:
            messagebox.showinfo("Slots", "Sélectionne d'abord un slot.", parent=self)
            return None
        slot = self.slots[int(selection[0]) - 1]
        if slot["infos"] is None:
            messagebox.showinfo(
                "Slots", f"Le slot {slot['numero']} est vide ou illisible.", parent=self)
            return None
        return slot

    def _demander_nom(self, seed: int, actuel: str = "") -> bool:
        """Demande un nom pour le monde et crée/renomme son dossier."""
        while True:
            nom = simpledialog.askstring(
                "Nom du monde", f"Nom du monde (seed {seed}) :",
                initialvalue=actuel, parent=self,
            )
            if nom is None:
                return False
            try:
                nommer_monde(seed, nom)
                return True
            except (ValueError, OSError) as erreur:
                messagebox.showerror("Nom du monde", str(erreur), parent=self)
                actuel = nom

    # --- Actions ---

    def nommer_selection(self) -> None:
        slot = self._slot_selectionne()
        if slot is None:
            return
        seed = slot["infos"]["seed"]
        dossier = self.mondes.get(seed)
        if self._demander_nom(seed, os.path.basename(dossier) if dossier else ""):
            self.actualiser()

    def deplacer_selection(self) -> None:
        slot = self._slot_selectionne()
        if slot is None:
            return
        seed = slot["infos"]["seed"]
        if seed not in self.mondes and not self._demander_nom(seed):
            return
        try:
            deplacer_slot_vers_monde(slot["numero"])
        except (ValueError, LookupError, OSError) as erreur:
            messagebox.showerror("Déplacement impossible", str(erreur), parent=self)
        self.actualiser()

    def renommer_monde(self) -> None:
        selection = self.arbre_mondes.selection()
        if not selection:
            messagebox.showinfo("Mondes", "Sélectionne d'abord un monde.", parent=self)
            return
        dossier = self.arbre_mondes.parent(selection[0]) or selection[0]
        seed = next(s for s, d in self.mondes.items() if d == dossier)
        if self._demander_nom(seed, os.path.basename(dossier)):
            self.actualiser()

    def copier_selection(self) -> None:
        selection = self.arbre_mondes.selection()
        if not selection or not self.arbre_mondes.parent(selection[0]):
            messagebox.showinfo(
                "Mondes", "Sélectionne d'abord une save dans un monde.", parent=self)
            return
        chemin = selection[0]

        libres = [str(s["numero"]) for s in self.slots if not s["existe"]]
        numero = simpledialog.askinteger(
            "Copier vers un slot",
            f"Slot de destination (1 à {NOMBRE_SLOTS}).\n"
            f"Slots libres : {', '.join(libres) if libres else 'aucun'}",
            minvalue=1, maxvalue=NOMBRE_SLOTS,
            initialvalue=int(libres[0]) if libres else None, parent=self,
        )
        if numero is None:
            return
        ecraser = False
        if os.path.exists(chemin_slot(numero)):
            ecraser = messagebox.askyesno(
                "Slot occupé",
                f"Le slot {numero} contient déjà une save.\n"
                "L'écraser ? Elle sera perdue si elle n'est pas rangée dans un monde.",
                icon="warning", default="no", parent=self,
            )
            if not ecraser:
                return
        try:
            copier_vers_slot(chemin, numero, ecraser=ecraser)
        except OSError as erreur:
            messagebox.showerror("Copie impossible", str(erreur), parent=self)
        self.actualiser()

    def _confirmer_suppression(self, chemin: str, description: str) -> None:
        confirme = messagebox.askyesno(
            "Supprimer la save",
            f"Supprimer {description} ?\n\nElle sera envoyée à la corbeille.",
            icon="warning", default="no", parent=self,
        )
        if not confirme:
            return
        try:
            supprimer_save(chemin)
        except OSError as erreur:
            messagebox.showerror("Suppression impossible", str(erreur), parent=self)
        self.actualiser()

    def supprimer_slot(self) -> None:
        selection = self.arbre_slots.selection()
        if not selection:
            messagebox.showinfo("Slots", "Sélectionne d'abord un slot.", parent=self)
            return
        slot = self.slots[int(selection[0]) - 1]
        if not slot["existe"]:
            messagebox.showinfo(
                "Slots", f"Le slot {slot['numero']} est déjà vide.", parent=self)
            return
        monde = self.arbre_slots.set(selection[0], "monde")
        self._confirmer_suppression(
            slot["chemin"], f"la save du slot {slot['numero']} — {monde}")

    def supprimer_save_monde(self) -> None:
        selection = self.arbre_mondes.selection()
        if not selection or not self.arbre_mondes.parent(selection[0]):
            messagebox.showinfo(
                "Mondes", "Sélectionne d'abord une save dans un monde.", parent=self)
            return
        chemin = selection[0]
        monde = os.path.basename(os.path.dirname(chemin))
        self._confirmer_suppression(
            chemin, f"« {os.path.basename(chemin)} » du monde « {monde} »")

    def ouvrir_dossier(self) -> None:
        selection = self.arbre_mondes.selection()
        if selection:
            dossier = self.arbre_mondes.parent(selection[0]) or selection[0]
        else:
            dossier = DOSSIER_MONDES
        if os.path.isdir(dossier):
            os.startfile(dossier)
        else:
            messagebox.showinfo("Mondes", "Aucun monde n'a encore été créé.", parent=self)


if __name__ == "__main__":
    GestionnaireSaves().mainloop()
