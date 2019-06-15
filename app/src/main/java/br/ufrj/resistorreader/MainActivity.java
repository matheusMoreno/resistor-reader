package br.ufrj.resistorreader;

import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;
import android.support.v4.content.FileProvider;
import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.theartofdev.edmodo.cropper.CropImage;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;


public class MainActivity extends AppCompatActivity {

    static final int REQUEST_TAKE_PHOTO = 1;
    static final int REQUEST_IMAGE_CAPTURE = 1;
    String rawPhotoPath = "empty";
    String croppedPhotoPath = "empty";
    private static final String TAG = "MyActivity";
    Uri photoURI = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        Button takePhotoButton = findViewById(R.id.buttonTakePicture);

        takePhotoButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                dispatchTakePictureIntent();
            }
        });
    }

    /** Chamada apos a tirada da foto, para processar a foto com testPython. */
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {

        if (requestCode == REQUEST_IMAGE_CAPTURE && resultCode == RESULT_OK) {
            imageCrop();
        }

        if (requestCode == CropImage.CROP_IMAGE_ACTIVITY_REQUEST_CODE) {
            saveCroppedImage(resultCode, data);

            String message = "Lendo resistor...";

            /* Mudar o texto em textSucess. */
            TextView textView = findViewById(R.id.textSucess);
            textView.setText(message);

            /* Para debug (ver a foto cortada direitinho). */
            File imgFile = new  File(croppedPhotoPath);

            if(imgFile.exists()){
                Bitmap myBitmap = BitmapFactory.decodeFile(imgFile.getAbsolutePath());
                ImageView myImage = findViewById(R.id.imageviewTest);
                myImage.setImageBitmap(myBitmap);
            }

            /* Ver o tempo que demora pra chamar o Python... */
            textView.setText(testPython(croppedPhotoPath));
        }
    }

    /** Cria o arquivo para salvar a imagem. */
    private File createImageFile(boolean isCropped) throws IOException {
        // Criar um novo arquivo com a foto do resistor
        String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(new Date());
        String imageFileName = "JPEG_" + timeStamp + "_";
        File storageDir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
        File image = File.createTempFile(
                imageFileName,  /* prefix */
                ".jpg",         /* suffix */
                storageDir      /* directory */
        );

        /* Pega o caminho absoluto da imagem. */
        if (isCropped)
            croppedPhotoPath = image.getAbsolutePath();
        else
            rawPhotoPath = image.getAbsolutePath();
        return image;
    }

    /** Cria a intent de tirar a foto e a salva na pasta do programa. */
    private void dispatchTakePictureIntent() {
        Intent takePictureIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        // Precisamos ver se ha algum componente que resolve o Intent
        if (takePictureIntent.resolveActivity(getPackageManager()) != null) {
            // Criamos o arquivo em que sera salva a foto
            File photoFile = null;
            try {
                photoFile = createImageFile(false);
            } catch (IOException ex) {
                Log.i(TAG, "IOException");
            }
            // E continuamos apenas se o arquivo foi criado corretamente
            if (photoFile != null) {
                photoURI = FileProvider.getUriForFile(this,
                        "br.ufrj.resistorreader.fileprovider", photoFile);
                takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, photoURI);
                startActivityForResult(takePictureIntent, REQUEST_TAKE_PHOTO);
            }
        }
    }

    /** Inicia a activity para cortar a foto tirada. */
    private void imageCrop() {
        if (photoURI != null) {
            CropImage.activity(photoURI).start(this);
        }
    }

    /** Metodo que salva a foto cortada na pasta do aplicativo. */
    private void saveCroppedImage(int resultCode, Intent data) {
        CropImage.ActivityResult result = CropImage.getActivityResult(data);

        /* Se o corte foi feito corretamente, salvamos a foto cortada para o Python. */
        if (resultCode == RESULT_OK) {
            Uri croppedUri = result.getUri();
            File croppedFile = null;
            Bitmap bitmap = null;

            try {
                bitmap = MediaStore.Images.Media.getBitmap(this.getContentResolver(), croppedUri);
            } catch (IOException e) {
                Log.d(TAG, "Error getting bitmap!!");
            }

            /* Novamente, checamos se e possivel criar o arquivo. */
            try {
                croppedFile = createImageFile(true);
            } catch (IOException ex) {
                Log.i(TAG, "IOException");
            }

            /* Se o arquivo for criado com sucesso, salvamos o bitmap. */
            try {
                if (croppedFile != null && bitmap != null) {
                    FileOutputStream fos = new FileOutputStream(croppedFile);
                    bitmap.compress(Bitmap.CompressFormat.PNG, 100, fos);
                    fos.close();
                } else {
                    Log.i(TAG, "IOException");
                }
            } catch (FileNotFoundException e) {
                Log.d(TAG, "File not found: " + e.getMessage());
            } catch (IOException e) {
                Log.d(TAG, "Error accessing file: " + e.getMessage());
            }
        } else if (resultCode == CropImage.CROP_IMAGE_ACTIVITY_RESULT_ERROR_CODE) {
            Log.i(TAG, "ERROR!!");
        }
    }

    /** Chama o modulo em Python para tratar a imagem. */
    private String testPython(String filename) {
        Python py = Python.getInstance();
        PyObject mod = py.getModule("reader");

        return mod.callAttr("read_resistor", filename).toString();
    }
}