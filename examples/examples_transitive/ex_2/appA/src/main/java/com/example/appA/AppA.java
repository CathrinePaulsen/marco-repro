package com.example.appA;

import java.lang.reflect.*;
import com.example.appB.AppB;
import com.example.appC.AppC;

/**
 * Hello world!
 *
 */
public class AppA
{
    public static void main( String[] args )
    {
        System.out.println( "Hello World from A!" );
        AppB.method("A");

        try {
//            Class<?> cls = Class.forName("com.example.appC.AppC");
            Method mtd = AppC.class.getMethod("method", String.class);
            mtd.invoke(null, "A (via reflection)");
        } catch (Exception e)
        {
            e.printStackTrace();
        }
    }

    public static void method(String from) {
        System.out.println(from + " just called this method from A");
    }
}














