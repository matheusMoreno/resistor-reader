package br.ufrj.resistorreader;

import android.content.Intent;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;
import android.support.v4.content.FileProvider;
import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;

import java.io.File;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;


public class MainActivity extends AppCompatActivity {

    static final int REQUEST_TAKE_PHOTO = 1;
    static final int REQUEST_IMAGE_CAPTURE = 1;
    String currentPhotoPath;
    private static final String TAG = "MyActivity";

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
            String message = "Lendo resistor...";

            /* Mudar o texto em textSucess. */
            TextView textView = findViewById(R.id.textSucess);
            textView.setText(message);

            /* Ver o tempo que demora pra chamar o Python... */
            textView.setText(testPython(currentPhotoPath));
        }
    }

    /** Cria o arquivo para salvar a imagem. */
    private File createImageFile() throws IOException {
        // Criar um novo arquivo com a foto do resistor
        String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(new Date());
        String imageFileName = "JPEG_" + timeStamp + "_";
        File storageDir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
        File image = File.createTempFile(
                imageFileName,  /* prefix */
                ".jpg",         /* suffix */
                storageDir      /* directory */
        );

        // Pega o caminho absoluto da imagem
        currentPhotoPath = image.getAbsolutePath();
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
                photoFile = createImageFile();
            } catch (IOException ex) {
                Log.i(TAG, "IOException");
            }
            // E continuamos apenas se o arquivo foi criado corretamente
            if (photoFile != null) {
                Uri photoURI = FileProvider.getUriForFile(this,
                        "br.ufrj.resistorreader.fileprovider", photoFile);
                takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, photoURI);
                startActivityForResult(takePictureIntent, REQUEST_TAKE_PHOTO);
            }
        }
    }

    /** Chama o modulo em Python para tratar a imagem. */
    private String testPython(String filename) {
        Python py = Python.getInstance();
        PyObject mod = py.getModule("test");

        return mod.callAttr("f", filename).toString();
    }
}