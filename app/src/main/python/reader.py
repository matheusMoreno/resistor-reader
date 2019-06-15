import numpy as np
import cv2

# Valores de resistores da serie E12
values = {10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82}

# Valor minimo que pode ser lido (valor de 3 faixas)
Rmin = 100

# Valor maximo que pode ser lido (valor maximo no laboratorio)
Rmax = 10000000

# Contraste a ser aplicado nas fotos
contrast = 50

# Limites RGB para as cores a serem detectadas. Esses limites
# foram encontrados empiricamente por meio de testes com fotos
# de resistores tiradas pelos desenvolvedores.
bgr_boundaries = [
   ([0, 0, 0], [120, 120, 120]),                # 0 - Preto ok
   ([10, 30, 100], [80, 80, 150]),              # 1 - Marrom MELHORAR
   ([0, 0, 160], [70, 70, 255]),                # 2 - Vermelho ok
   ([0, 80, 190], [90, 140, 255]),              # 3 - Laranja MELHORAR?
   ([0, 160, 190], [90, 255, 255]),             # 4 - Amarelo ok
   ([10, 100, 10], [90, 255, 90]),              # 5 - Verde MELHORAR (CONFUNDIDO COM PRETO PARA 150K)
   ([80, 5, 0], [255, 200, 50]),                # 6 - Azul ok
   ([65, 0, 65], [230, 65, 255]),              # 7 - Roxo ok (supostamente, testei todos com e foi)
   ([220, 220, 220], [220, 220, 220]),          # 8 - Cinza ########parece ok melhor testar mais
   ([160, 160, 160], [205, 205, 205]),          # 9 - Branco ok
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

      inc = -1 if (mean > 165) else 1

   return img



# Funcao que checa se um valor existe ou nao
def check_value(contours):
   if len(contours) < 3:
      return False

   if not (contours[0][0]*10 + contours[1][0]) in values or \
      (contours[0][0]*10 + contours[1][0]) * (10 ** contours[2][0]) > Rmax or \
      (contours[0][0]*10 + contours[1][0]) * (10 ** contours[2][0]) < Rmin:
      return False

   return True


# Formata o resultado. Esta ruim! Precisa ser consertada.
def format_result(result):
   if result < 10**3:
      return str(result) + " \u03A9"


   result = result / 10**3
   if result.is_integer():
      result = int(result)

   if result < 10**3:
      return str(result) + " k\u03A9"


   result = result / 10**3
   if result.is_integer():
      result = int(result)

   return str(result / 10**6) + " M\u03A9"



def read_resistor(filename):
   # Abrimos a imagem e pegamos um passo h a ser usado
   img = cv2.imread(filename)
   rows, _, _ = img.shape
   h = round(rows/20)

   # Vetor com os cortes usados, e outro com os contornos encontrados
   crops = []
   contours = []


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

      crops[-1] = np.int16(crops[-1])
      crops[-1] = crops[-1] * (contrast/127+1) - contrast
      crops[-1] = np.clip(crops[-1], 0, 255)
      crops[-1] = np.uint8(crops[-1])

      crops[-1] = set_brightness(crops[-1])
      print(crops[-1].mean())


   for k in range(0, 10):
      final = np.zeros((2*h,len(img[0]),3), np.uint8)

      for crop in crops:

         # Tratamento da cor preta
         if k == 0:
            crop = np.int16(crop)
            crop = crop + 100
            crop = np.clip(crop, 0, 255)
            crop = np.uint8(crop)

         # Geramos uma mascara na versao cortada, com a cor que queremos
         mask = cv2.inRange(crop, np.array(bgr_boundaries[k][0]), np.array(bgr_boundaries[k][1]))

         # Fazemos um and da mascara com o corte
         res = cv2.bitwise_and(crop, crop, mask = mask)

         # Adicionamos o resultado da iteracao pro resultado final
         final = cv2.add(final, res)

      # Transforma todos os pixels nao nulos em branco. Para a deteccao de contornos.
      final[np.where((final > [0, 0, 0]).all(axis = 2))] = [255,255,255]

      gray = cv2.cvtColor(final,cv2.COLOR_BGR2GRAY)
      gray = cv2.GaussianBlur(gray, (3, 3), 0)
      _, detected, _ = cv2.findContours(gray.copy(), 1, 1)

      # Pega a area e a posicao em x do contorno.
      for c in detected:
         m = cv2.moments(c)

         if m['m00'] != 0:
            xpos = int(m['m10']/m['m00'])
         else:
            xpos = -1

         contours.append([k, cv2.contourArea(c), xpos])

   # Ordenamos os contornos pelo tamanho e pegamos as 3 maiores
   contours.sort(key=lambda row: row[1], reverse=True)
   contours = contours[:3]

   # Ordenamos pela posicao em x...
   contours.sort(key=lambda row: row[2])

   # E checamos se o valor existe.
   if not check_value(contours):
      contours.reverse()

      if not check_value(contours):
         return "Error E-1: Value not found"


   # Escrevemos o valor.
   value = (contours[0][0]*10 + contours[1][0]) * (10 ** contours[2][0])
   return format_result(value)
