import numpy as np
import cv2


def set_brightness_contrast(img, b_low, b_high, contrast):
   """
   Funcao de ajuste do brilho e contraste da imagem.
   Define os valores para permanecerem
   dentro do intervalo [b_low, b_high] de brilho.

   Entrada: img      - Imagem original.
            b_low    - Valor de referencia inferior para o ajuste de brilho.
            b_high   - Valor de referencia superior para o ajuste de brilho.
            contrast - Valor de referencia para o ajuste de contraste.

   Saida:   img      - Imagem com a aplicacao do ajuste de brilho.
   """

   mean = img.mean()
   inc = 1

   while (mean < b_low) or (mean > b_high):
      img = np.int16(img)
      img = img + inc
      img = np.clip(img, 0, 255)
      img = np.uint8(img)

      mean = img.mean()

      inc = -1 if (mean > ((b_low + b_high) / 2)) else 1

   img = np.int16(img)
   img = img * (contrast/127+1) - contrast
   img = np.clip(img, 0, 255)
   img = np.uint8(img)

   return img


# Funcao de pre-processamento e reprocessamento da imagem
def img_process(img, h, b_low, b_high, contrast):
   """
   Funcao de pre-processamento e reprocessamento da imagem para determinacao das cores.
   Define um intervalo especifico no meio da imagem para pre-processar,
   ou a imagem inteira para reprocessar fazendo ajuste de brilho e contraste.

   Entradas: img      - Imagem original.
             h        - Intervalo de linhas da imagem original utilizado.
             b_low    - Valor de referencia inferior para o ajuste de brilho.
             b_high   - Valor de referencia superior para o ajuste de brilho.
             contrast - Valor de referencia para o ajuste de contraste.

   Saida:    crops    - Pedacos da imagem pre-processados e prontos para serem analisados.
   """

   crops = []
   means = []

   # Pegamos, das 5 faixas centrais, as 3 de menor brilho
   for i in range(5, 15, 2):
      crop = img[i*h:i*h + 2*h, :]
      means.append([i, crop.mean()])

   means.sort(key=lambda row: row[1:])
   index = np.array(means)[:3,0]
   index = [int(x) for x in index]


   # Melhoramos o contraste e o brilho dos cortes
   for i in index:
      crops.append(img[i*h:i*h + 2*h, :])
      crops[-1] = set_brightness_contrast(crops[-1], b_low, b_high, contrast)

   return crops


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


# Funcao que processa as cores e determina os valores encontrados
def find_contours(crops, h, length):
   """
   Funcao de processamento das cores, definicao de contornos
   e atribuicao de valores a imagem do resistor analisada.

   Entradas: crops    - Imagem sendo analisada (parte central da imagem original, ja pre-processada).
             h        - Intervalo de linhas da imagem original utilizado.
             length   - Tamanho a imagem original.

   Saida:    contours - Valores encontrados para cada contorno analisado, referentes as cores descobertas.
   """

   # Limites RGB para as cores a serem detectadas. Esses limites
   # foram encontrados empiricamente por meio de testes com fotos
   # de resistores tiradas pelos desenvolvedores.
   bgr_boundaries = [
      ([0, 0, 0], [95, 95, 95]),                  # 0 - Preto OK
      ([0, 25, 75], [90, 100, 155]),              # 1 - Marrom OK
      ([0, 0, 156], [85, 85, 255]),               # 2 - Vermelho OK
      ([0, 60, 170], [70, 165, 255]),             # 3 - Laranja OK
      ([0, 170, 170], [90, 255, 255]),            # 4 - Amarelo OK
      ([0, 70, 0], [120, 255, 90]),               # 5 - Verde OK
      ([150, 30, 0], [255, 200, 80]),             # 6 - Azul OK
      ([80, 10, 40], [210, 90, 200]),             # 7 - Roxo OK
      ([80, 65, 10], [175, 125, 95]),             # 8 - Cinza OK

      # ALTEREI OS LIMIARES DO BRANCO, DE 210 PARA 255

      ([200, 200, 200], [255, 255, 255]),         # 9 - Branco
   ]

   contours = []
   kernel = np.ones((25, 25), np.uint8) # Kernel para configuracao do opening
   white_kernel = np.ones((30, 30), np.uint8) # Caso especifico de kernel para a cor branca

   # Matrizes usadas para detectar as cores
   # Thresholds definidos para os testes secundarios
   black_limit  = np.full((2*h, length), 25)
   brown_limit  = np.full((2*h, length), 30)
   red_limit    = np.full((2*h, length), 60)
   orange_limit = np.full((2*h, length), 30)
   green_limit  = np.full((2*h, length), 15)
   blue_limit   = np.full((2*h, length), 15)
   gray_limit   = np.full((2*h, length), 30)
   white_limit  = np.full((2*h, length), 3)

   # Procuramos uma cor pela imagem 3 vezes (pra cada crop)
   for k in range(0, 10):
      final = np.zeros((2*h,length,3), np.uint8)

      for crop in crops:
         # Geramos uma mascara na versao cortada, com a cor que queremos
         mask = cv2.inRange(crop, np.array(bgr_boundaries[k][0]), np.array(bgr_boundaries[k][1]))

         # Fazemos um and da mascara com o corte
         res = cv2.bitwise_and(crop, crop, mask=mask)

         if k == 0:
            black_mask = np.logical_or(np.abs(res[:,:,0].astype(int) - res[:,:,1]) > black_limit,
                                       np.abs(res[:,:,1].astype(int) - res[:,:,2]) > black_limit)
            black_mask = np.logical_or(np.abs(res[:,:,2].astype(int) - res[:,:,0]) > black_limit, black_mask)
            res[np.nonzero(black_mask)] = [0, 0, 0]

         elif k == 1:
            brown_mask = np.logical_or(res[:,:,2].astype(int) - res[:,:,0] < brown_limit,
                                       res[:,:,2].astype(int) - res[:,:,1] < brown_limit)
            res[np.nonzero(brown_mask)] = [0, 0, 0]

         elif k == 2:
            red_mask = np.logical_or(res[:,:,0].astype(int) + red_limit > res[:,:,2].astype(int),
                                     res[:,:,1].astype(int) + red_limit > res[:,:,2].astype(int))
            res[np.nonzero(red_mask)] = [0, 0, 0]

         elif k == 3:
            orange_mask = np.logical_or(res[:,:,0].astype(int) + orange_limit > res[:,:,1].astype(int),
                                        res[:,:,0].astype(int) + orange_limit + 20 > res[:,:,2].astype(int))
            res[np.nonzero(orange_mask)] = [0, 0, 0]

         elif k == 5:
            green_mask = np.logical_or(res[:,:,1].astype(int) - res[:,:,0] < green_limit,
                                       res[:,:,1].astype(int) - res[:,:,2] < green_limit + 20)
            res[np.nonzero(green_mask)] = [0, 0, 0]

         elif k == 6:
            blue_mask = np.logical_or(res[:,:,0].astype(int) - res[:,:,1] < blue_limit,
                                      res[:,:,0].astype(int) - res[:,:,2] < blue_limit + 50)
            res[np.nonzero(blue_mask)] = [0, 0, 0]

         elif k == 7:
            purple_mask = np.logical_or(res[:,:,1].astype(float) + 15 > res[:,:,2],
                                        res[:,:,1].astype(float) + 35 > res[:,:,0])
            res[np.nonzero(purple_mask)] = [0, 0, 0]

         elif k == 8:
            gray_mask = np.logical_or(abs((res[:,:,0].astype(float) / 2) - (res[:,:,1].astype(float) / 2)) > \
                                      gray_limit,
                                      (abs(res[:,:,0].astype(float) / 2) - (res[:,:,2].astype(float) / 2)) > \
                                      gray_limit + 15)
            res[np.nonzero(gray_mask)] = [0, 0, 0]

         elif k == 9:
            white_mask = np.logical_or(np.logical_or(res[:,:,0].astype(int) - res[:,:,1] > white_limit,
                                                     res[:,:,0].astype(int) - res[:,:,2] > white_limit + 20),
                                       res[:,:,1].astype(int) - res[:,:,2] > white_limit + 20)
            res[np.nonzero(white_mask)] = [0, 0, 0]

         # Adicionamos o resultado da iteracao pro resultado final
         final = cv2.add(final, res)

      # Transforma todos os pixels nao nulos em branco, para a deteccao de contornos.
      final[np.where((final != [0, 0, 0]).all(axis = 2))] = [255, 255, 255]

      # Faz um opening (erosao + dilatacao) para a remocao de ruidos.
      # Para o caso especifico da cor branca, o kernel do opening e maior.
      if k == 9:
         final = cv2.morphologyEx(final, cv2.MORPH_OPEN, white_kernel)
      else:
         final = cv2.morphologyEx(final, cv2.MORPH_OPEN, kernel)

      # Deteccao de contornos
      gray = cv2.cvtColor(final,cv2.COLOR_BGR2GRAY)
      _, detected, _ = cv2.findContours(gray.copy(), 1, 1)

      # Pega a area e a posicao em x do contorno.
      for c in detected:
         m = cv2.moments(c)
         xpos = int(m['m10']/m['m00']) if m['m00'] != 0 else -1
         contours.append([k, cv2.contourArea(c), xpos])

   return contours


# Funcao de tratamento apos a analise correta das cores
def contour_treat(contours):
   """
   Funcao que ordena os valores descobertos para os contornos
   de acordo com sua posicao na imagem analisada, tamanho do contorno e ordem de prioridade.

   Entrada: contours - Valores de cada contorno disposto originalmente.

   Saida:   contours - Valores de cada contorno ordenados.
   """

   # ATENCAO AQUI, MORENO! ESSA EH A PARTE NOVA QUE UTILIZA A LOGICA DE ORDEM DE PRIORIDADE
   contours_aux = []

   # Primeiro, definimos quais contornos ocupam mais ou menos a mesma posicao.
   # Caso existam mais de 1, consideramos somente o de menor valor de referencia.
   for i in range(len(contours)):
      for j in range(len(contours)):
         if abs(contours[i][2] - contours[j][2]) < 5:
            if contours[i][0] < contours[j][0] and contours[i] not in contours_aux:
               contours_aux.append(contours[i])
            elif contours[i][0] > contours[j][0] and contours[j] not in contours_aux:
               contours_aux.append(contours[j])

   control = 0

   # Depois, completamos a lista auxiliar com todos os casos que nao
   # estavam na mesma posicao e com os casos que, na mesma posicao,
   # mesmo tendo valor de referencia maior, tem tamanho igual ou maior
   # que duas vezes o tamanho do concorrente
   for k in range(len(contours)):
      if contours[k] not in contours_aux:
         for m in range(len(contours_aux)):
            if abs(contours[k][2] - contours_aux[m][2]) < 5:
               control = control + 1

               if contours[k][1] > 2*contours_aux[m][1]:
                  contours_aux.remove(contours_aux[m])
                  contours_aux.append(contours[k])

         if control == 0:
            contours_aux.append(contours[k])

   # E atribuimos a lista auxiliar a lista original para continuarmos
   # o tratamento
   contours = contours_aux

   # Alem disso, tratamos os contornos para os casos de ruido branco
   contours_noiseless = []
   contours_final = []
   sum_size_contours = 0

   for i in range (len(contours)):
      if contours[i][0] != 9:
         contours_noiseless.append(contours[i])

   for j in range (len(contours_noiseless)):
      sum_size_contours = sum_size_contours + contours_noiseless[j][1]

   mean_size_contours = sum_size_contours / len(contours_noiseless) if len(contours_noiseless) > 0 \
                        else 0

   for k in range (len(contours_noiseless)):
      if contours_noiseless[k][1] > 0.6 * mean_size_contours:
         contours_final.append(contours_noiseless[k])

   if len(contours_final) < 3:
      for m in range(len(contours)):
         if contours[m] not in contours_final:
            contours_final.append(contours[m])

   contours = contours_final


   # Ordenamos os contornos pelo tamanho e pegamos as 3 maiores
   contours.sort(key=lambda row: row[1], reverse=True)
   contours = contours[:3]

   # Ordenamos pela posicao em x.
   contours.sort(key=lambda row: row[2])

   return contours


# Funcao que checa se um valor existe ou nao
def check_value(contours, length):
   """
   Funcao que verifica a existencia de um valor de resistor encontrado.
   Inverte o sentido de contours se a distancia do menor x ate o inicio
   da imagem for maior que a distancia do maior x ao fim (o que implica
   que o resistor esta invertido).

   Entrada: contours - Valores do resistor a serem testados.

   Saida:   True or False.
   """

   # Valores de resistores da serie E12
   values = {10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82}

   # Valor minimo que pode ser lido (valor de 3 faixas)
   rmin = 100

   # Valor maximo que pode ser lido (valor maximo no laboratorio)
   rmax = 10000000

   if len(contours) < 3:
      return False

   if contours[0][2] > (length - contours[2][2]):
      contours.reverse()

   if not (contours[0][0]*10 + contours[1][0]) in values or \
           (contours[0][0]*10 + contours[1][0]) * (10 ** contours[2][0]) > rmax or \
           (contours[0][0]*10 + contours[1][0]) * (10 ** contours[2][0]) < rmin:
      return False

   return True



# Funcao principal
def read_resistor(filename):
   """
   Funcao de leitura do valor do resistor atraves do
   processamento da imagem de entrada.

   Entradas: filename - Nome do arquivo da imagem de entrada.

   Saida:    string   - Valor do resistor ou erro de leitura.
   """

   # Abrimos a imagem e definimos um passo h a ser utilizado
   img = cv2.imread(filename)
   rows, length, _ = img.shape
   h = round(rows/20)

   # Valores iniciais de referencia para contraste e brilho
   contrast = 75
   b_low = 150
   b_high = 180

   crops = img_process(img, h, b_low, b_high, contrast)

   # Processamos a imagem para descobrir os valores
   contours = find_contours(crops, h, length)

   # Apos encontrar as cores do resistor da imagem,
   # fazemos o tratamento dos valores encontrados para
   # definir se sao validos ou nao
   contours = contour_treat(contours)
   success = check_value(contours, length)

   tries = 0

   while tries < 3 and not success:
      contrast = contrast + 25
      # b_low = b_low + 10
      # b_high = b_high + 10
      crops = img_process(img, h, b_low, b_high, contrast)

      contours = find_contours(crops, h, length)

      contours = contour_treat(contours)
      success = check_value(contours, length)

      tries = tries + 1

   # Escrevemos o valor.
   if success:
      value = (contours[0][0]*10 + contours[1][0]) * (10 ** contours[2][0])
      return format_result(value)
   else:
      return 'err'