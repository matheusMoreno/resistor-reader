import numpy as np
import cv2

# Valores de resistores da serie E12
values = {10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82}

# Valor minimo que pode ser lido (valor de 3 faixas)
Rmin = 100

# Valor maximo que pode ser lido (valor maximo no laboratorio)
Rmax = 10000000

# Contraste a ser aplicado nas fotos
contrast = 75

length = 0

# Limites RGB para as cores a serem detectadas. Esses limites
# foram encontrados empiricamente por meio de testes com fotos
# de resistores tiradas pelos desenvolvedores.
bgr_boundaries = [
   ([0, 0, 0], [65, 65, 65]),                  # 0 - Preto OK
   ([10, 25, 70], [80, 80, 150]),              # 1 - Marrom OK
   ([0, 0, 160], [75, 75, 255]),               # 2 - Vermelho OK
   ([0, 61, 170], [60, 140, 255]),             # 3 - Laranja OK
   ([0, 170, 170], [90, 255, 255]),            # 4 - Amarelo OK
   ([0, 85, 0], [85, 255, 85]),                # 5 - Verde OK
   ([150, 30, 0], [255, 200, 90]),             # 6 - Azul OK
   ([80, 15, 60], [180, 90, 180]),             # 7 - Roxo OK
   ([80, 65, 10], [185, 125, 90]),             # 8 - Cinza OK
   ([205, 205, 205], [230, 230, 230]),         # 9 - Branco
]


# Funcao que coloca o brilho da imagem entre 160 +- 15, para homogeneidade
def set_brightness(img):
   mean = img.mean()
   inc = 1

   while (mean < 145) or (mean > 175):
      img = np.int16(img)
      img = img + inc
      img = np.clip(img, 0, 255)
      img = np.uint8(img)

      mean = img.mean()

      inc = -1 if (mean > 160) else 1

   return img


# Funcao que checa se um valor existe ou nao
def check_value(contours):
   if len(contours) < 3:
      return False

   if contours[2][2] < (length - contours[0][2]):
      contours.reverse()

   if not (contours[0][0]*10 + contours[1][0]) in values or \
      (contours[0][0]*10 + contours[1][0]) * (10 ** contours[2][0]) > Rmax or \
      (contours[0][0]*10 + contours[1][0]) * (10 ** contours[2][0]) < Rmin:
      return False

   return True


# Formata o resultado.
def format_result(result):
   # Se < 1000, simplesmente retornamos o resultado
   if result < 10**3:
      return str(result) + " \u03A9"

   # Se < 1M, precisamos tratar a primeira casa decimal
   elif result < 10**6:
      decimal = (result % 10**3) // 100
      if decimal > 0:
         return str(result // 10**3) + "." + str(decimal) + " k\u03A9"
      else:
         return str(result // 10**3) + " k\u03A9"

   # Se nenhum dos dois casos, > 1M.
   decimal = (result % 10**6) // 10**5
   if decimal > 0:
      return str(result // 10**6) + "." + str(decimal) + " M\u03A9"
   else:
      return str(result // 10**6) + " M\u03A9"



def read_resistor(filename):
   # Abrimos a imagem e pegamos um passo h a ser usado
   img = cv2.imread(filename)
   rows, length, _ = img.shape
   h = round(rows/20)

   # Vetor com os cortes usados, e outro com os contornos encontrados
   crops = []
   contours = []

   # Kernel que sera usado na opening (erosao + dilatacao)
   kernel = np.ones((25, 25), np.uint8)

   # Pegamos, das 5 faixas centrais, as 3 de menor brilho
   means = []
   for i in range(5, 15, 2):
      crop = img[i*h:i*h + 2*h, :]
      means.append([i, crop.mean()])

   means.sort(key=lambda row: row[1:])
   index = np.array(means)[:3,0]
   index = [int(x) for x in index]


   # Melhoramos o contraste e o brilho dos cortes
   for i in index:
      crops.append(img[i*h:i*h + 2*h, :])

      crops[-1] = set_brightness(crops[-1])
      print(crops[-1].mean())

      crops[-1] = np.int16(crops[-1])
      crops[-1] = crops[-1] * (contrast/127+1) - contrast
      crops[-1] = np.clip(crops[-1], 0, 255)
      crops[-1] = np.uint8(crops[-1])


   # Procuramos cada cor nos cortes selecionados
   for k in range(0, 10):
      final = np.zeros((2*h,len(img[0]),3), np.uint8)

      for crop in crops:
         # Geramos uma mascara na versao cortada, com a cor que queremos
         mask = cv2.inRange(crop, np.array(bgr_boundaries[k][0]), np.array(bgr_boundaries[k][1]))

         # Fazemos um and da mascara com o corte
         res = cv2.bitwise_and(crop, crop, mask = mask)

         # Adicionamos o resultado da iteracao pro resultado final
         final = cv2.add(final, res)

      # Transforma todos os pixels nao nulos em branco, para a deteccao de contornos
      final[np.where((final != [0, 0, 0]).all(axis = 2))] = [255, 255, 255]

      # Faz o processo de opening (erosao + dilatacao) para remover ruidos
      final = cv2.morphologyEx(final, cv2.MORPH_OPEN, kernel)

      # Detecta os contornos
      gray = cv2.cvtColor(final, cv2.COLOR_BGR2GRAY)
      _, detected, _ = cv2.findContours(gray.copy(), 1, 1)

      # Pega a area e a posicao em x do contorno
      for c in detected:
         m = cv2.moments(c)
         xpos = int(m['m10']/m['m00']) if m['m00'] != 0 else -1
         contours.append([k, cv2.contourArea(c), xpos])

   # Removemos qualquer contorno de posicao -1 e ordenamos os contornos restantes
   # pelo tamanho, pegando os 3 maiores
   contours = [c for c in contours if c[2] != -1]
   contours.sort(key=lambda row: row[1], reverse=True)
   contours = contours[:3]

   # Ordenamos pela posicao em x...
   contours.sort(key=lambda row: row[2])

   # E checamos se o valor existe
   if not check_value(contours):
      return "err (value not found!)"

   # Escrevemos o valor
   value = (contours[0][0]*10 + contours[1][0]) * (10 ** contours[2][0])
   return format_result(value)
