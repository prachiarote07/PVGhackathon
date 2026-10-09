package com.moneyfy.app;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.security.NetworkSecurityPolicy;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;
import org.junit.runner.RunWith;

/** Native checks to run with connectedDebugAndroidTest after SDK/device setup. */
@RunWith(AndroidJUnit4.class)
public class MoneyFyShellTest {
    @Test
    public void packagedIdentityAndNetworkPolicy() {
        Context context = InstrumentationRegistry.getInstrumentation().getTargetContext();
        assertEquals("com.moneyfy.app", context.getPackageName());
        assertEquals("MoneyFy", context.getString(R.string.app_name));
        assertFalse(NetworkSecurityPolicy.getInstance().isCleartextTrafficPermitted());
        assertFalse((context.getApplicationInfo().flags & ApplicationInfo.FLAG_ALLOW_BACKUP) != 0);
    }
}
