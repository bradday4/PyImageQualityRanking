import numpy as np


def azimuthal_average(image, **kwargs):
    """
    Calculate the azimuthally averaged radial profile.

    image - The 2D image
    center - The [x,y] pixel coordinates used as the center. The default is
             None, which then uses the center of the image (including
             fractional pixels).
    stddev - if specified, return the azimuthal standard deviation instead of the average
    returnradii - if specified, return (radii_array,radial_profile)
    return_nr   - if specified, return number of pixels per radius *and* radius
    binsize - size of the averaging bin.  Can lead to strange results if
        non-binsize factors are used to specify the center and the binsize is
        too large
    weights - can do a weighted average instead of a simple average if this keyword parameter
        is set.  weights.shape must = image.shape.  weighted stddev is undefined, so don't
        set weights and stddev.
    steps - if specified, will return a double-length bin array and radial
        profile so you can plot a step-form radial profile (which more accurately
        represents what's going on)
    interpnan - Interpolate over NAN values, i.e. bins where there is no data?
        left,right - passed to interpnan; they set the extrapolated values
    mask - can supply a mask (boolean array same size as image with True for OK and False for not)
        to average over only select data.

    If a bin contains NO DATA, it will have a NAN value because of the
    divide-by-sum-of-weights component.  I think this is a useful way to denote
    lack of data, but users let me know if an alternative is prefered...

    """

    center = kwargs.get("center", None)
    stddev = kwargs.get("stddev", False)
    returnradii = kwargs.get("returnradii", False)
    return_nr = kwargs.get("return_nr", False)
    binsize = kwargs.get("binsize", 0.5)
    weights = kwargs.get("weights", None)
    steps = kwargs.get("steps", False)
    interpnan = kwargs.get("interpnan", False)
    left = kwargs.get("left", None)
    right = kwargs.get("right", None)
    mask = kwargs.get("mask", None)
    sum_bin = kwargs.get("sum_bin", False)

    # Calculate the indices from the image
    y, x = np.indices(image.shape)

    if center is None:
        center = np.array([(x.max() - x.min()) / 2.0, (y.max() - y.min()) / 2.0])

    # Convert FFT image into polar form. Exclude frequencies higher than
    # the sampling frequency
    r = np.hypot(x - center[0], y - center[1])

    if weights is None:
        weights = np.ones(image.shape)
    elif stddev:
        raise ValueError("Weighted standard deviation is not defined.")

    if mask is None:
        # mask is only used in a flat context
        mask = np.ones(image.shape, dtype="bool").ravel()
    elif len(mask.shape) > 1:
        mask = mask.ravel()

    # the 'bins' as initially defined are lower/upper bounds for each bin
    # so that values will be in [lower,upper)
    nbins = int((np.round(r.max() / binsize) + 1))
    maxbin = nbins * binsize
    bins = np.linspace(0, maxbin, nbins + 1)
    # but we're probably more interested in the bin centers than their left or right sides...
    bin_centers = (bins[1:] + bins[:-1]) / 2.0

    # Find out which radial bin each point in the map belongs to
    whichbin = np.digitize(r.flat, bins)

    # how many per bin (i.e., histogram)?
    # there are never any in bin 0, because the lowest index returned by digitize is 1
    nr = np.bincount(whichbin)[1:]

    # recall that bins are from 1 to nbins (which is expressed in array terms by arange(nbins)+1 or xrange(1,nbins+1) )
    # radial_prof.shape = bin_centers.shape
    sampling_freq = (x.max() - x.min()) / 2.0
    nbins_true = int(sampling_freq / binsize)
    bin_centers = bin_centers[0:nbins_true]
    if stddev:
        radial_prof = np.array(
            [image.flat[mask * (whichbin == b)].std() for b in range(1, nbins + 1)]
        )
    elif sum_bin:
        radial_prof = np.array(
            [
                ((image * weights).flat[mask * (whichbin == b)].sum())
                for b in range(1, nbins_true + 1)
            ]
        )
    else:
        radial_prof = np.array(
            [
                ((image * weights).flat[mask * (whichbin == b)].sum())
                / (weights.flat[mask * (whichbin == b)].sum())
                for b in range(1, nbins_true + 1)
            ]
        )

    if interpnan:
        radial_prof = np.interp(
            bin_centers,
            bin_centers.ravel(),
            radial_prof.ravel(),
            left=left,
            right=right,
        )

    if steps:
        xarr = np.array(list(zip(bins[:-1], bins[1:]))).ravel()
        yarr = np.array(list(zip(radial_prof, radial_prof))).ravel()
        return xarr, yarr
    elif returnradii:
        return bin_centers, radial_prof
    elif return_nr:
        return nr, bin_centers, radial_prof
    else:
        return radial_prof


def azimuthal_average_bins(image, azbins, symmetric=None, center=None, **kwargs):
    """ Compute the azimuthal average over a limited range of angles """
    y, x = np.indices(image.shape)
    if center is None:
        center = np.array([(x.max() - x.min()) / 2.0, (y.max() - y.min()) / 2.0])

    theta = np.arctan2(x - center[0], y - center[1])
    theta[theta < 0] += 2 * np.pi
    theta_deg = theta * 180.0 / np.pi

    if not isinstance(azbins, np.ndarray):
        # pass
        if isinstance(azbins, int):
            if symmetric == 2:
                azbins = np.linspace(0, 90, azbins)
                theta_deg = theta_deg % 90
            elif symmetric == 1:
                azbins = np.linspace(0, 180, azbins)
                theta_deg = theta_deg % 180
            else:
                azbins = np.linspace(0, 360, azbins)
        else:
            raise ValueError("azbins must be an ndarray or an integer")

    azavlist = []
    for blow, bhigh in zip(azbins[:-1], azbins[1:]):
        mask = (theta_deg > (blow % 360)) * (theta_deg < (bhigh % 360))
        rr, zz = azimuthal_average(
            image, center=center, mask=mask, returnradii=True, **kwargs
        )
        azavlist.append(zz)

    return azbins, rr, azavlist


def radial_average(image, **kwargs):
    """
    Calculate the radially averaged azimuthal profile.

    image - The 2D image
    center - The [x,y] pixel coordinates used as the center. The default is
             None, which then uses the center of the image (including
             fractional pixels).
    stddev - if specified, return the radial standard deviation instead of the average
    return_az - if specified, return (azimuthArray,azimuthal_profile)
    return_naz   - if specified, return number of pixels per azimuth *and* azimuth
    binsize - size of the averaging bin.  Can lead to strange results if
        non-binsize factors are used to specify the center and the binsize is
        too large
    weights - can do a weighted average instead of a simple average if this keyword parameter
        is set.  weights.shape must = image.shape.  weighted stddev is undefined, so don't
        set weights and stddev.
    steps - if specified, will return a double-length bin array and azimuthal
        profile so you can plot a step-form azimuthal profile (which more accurately
        represents what's going on)
    interpnan - Interpolate over NAN values, i.e. bins where there is no data?
        left,right - passed to interpnan; they set the extrapolated values
    mask - can supply a mask (boolean array same size as image with True for OK and False for not)
        to average over only select data.

    If a bin contains NO DATA, it will have a NAN value because of the
    divide-by-sum-of-weights component.  I think this is a useful way to denote
    lack of data, but users let me know if an alternative is prefered...

    """
    center = kwargs.get("center", None)
    stddev = kwargs.get("stddev", False)
    return_az = kwargs.get("return_az", False)
    return_naz = kwargs.get("return_naz", False)
    binsize = kwargs.get("binsize", 1.0)
    weights = kwargs.get("weights", None)
    steps = kwargs.get("steps", False)
    interpnan = kwargs.get("interpnan", False)
    left = kwargs.get("left", None)
    right = kwargs.get("right", None)
    mask = kwargs.get("mask", None)
    # Calculate the indices from the image
    y, x = np.indices(image.shape)

    if center is None:
        center = np.array([(x.max() - x.min()) / 2.0, (y.max() - y.min()) / 2.0])

    theta = np.arctan2(x - center[0], y - center[1])
    theta[theta < 0] += 2 * np.pi
    theta_deg = theta * 180.0 / np.pi

    if weights is None:
        weights = np.ones(image.shape)
    elif stddev:
        raise ValueError("Weighted standard deviation is not defined.")

    if mask is None:
        # mask is only used in a flat context
        mask = np.ones(image.shape, dtype="bool").ravel()
    elif len(mask.shape) > 1:
        mask = mask.ravel()

    # the 'bins' as initially defined are lower/upper bounds for each bin
    # so that values will be in [lower,upper)
    nbins = np.round(theta_deg.max() / binsize) + 1
    maxbin = nbins * binsize
    bins = np.linspace(0, maxbin, nbins + 1)
    # but we're probably more interested in the bin centers than their left or right sides...
    bin_centers = (bins[1:] + bins[:-1]) / 2.0

    # Find out which azimuthal bin each point in the map belongs to
    whichbin = np.digitize(theta_deg.flat, bins)

    # how many per bin (i.e., histogram)?
    # there are never any in bin 0, because the lowest index returned by digitize is 1
    nr = np.bincount(whichbin)[1:]

    # recall that bins are from 1 to nbins (which is expressed in array terms by arange(nbins)+1 or xrange(1,nbins+1) )
    # azimuthal_prof.shape = bin_centers.shape
    if stddev:
        azimuthal_prof = np.array(
            [image.flat[mask * (whichbin == b)].std() for b in range(1, nbins + 1)]
        )
    else:
        azimuthal_prof = np.array(
            [
                ((image * weights).flat[mask * (whichbin == b)].sum())
                / (weights.flat[mask * (whichbin == b)].sum())
                for b in range(1, nbins + 1)
            ]
        )

    if interpnan:
        azimuthal_prof = np.interp(
            bin_centers,
            bin_centers.ravel(),
            azimuthal_prof.ravel(),
            left=left,
            right=right,
        )

    if steps:
        xarr = np.array(list(zip(bins[:-1], bins[1:]))).ravel()
        yarr = np.array(list(zip(azimuthal_prof, azimuthal_prof))).ravel()
        return xarr, yarr
    elif return_az:
        return bin_centers, azimuthal_prof
    elif return_naz:
        return nr, bin_centers, azimuthal_prof
    else:
        return azimuthal_prof


def radial_average_bins(image, radbins, corners=True, center=None, **kwargs):
    """ Compute the radial average over a limited range of radii """
    y, x = np.indices(image.shape)
    if center is None:
        center = np.array([(x.max() - x.min()) / 2.0, (y.max() - y.min()) / 2.0])
    r = np.hypot(x - center[0], y - center[1])

    if not isinstance(radbins, np.ndarray):
        # pass
        if isinstance(radbins, int):
            if corners:
                radbins = np.linspace(0, r.max(), radbins)
            else:
                radbins = np.linspace(
                    0, np.max(np.abs(np.array([x - center[0], y - center[1]]))), radbins
                )
        else:
            raise ValueError("radbins must be an ndarray or an integer")

    radavlist = []
    for blow, bhigh in zip(radbins[:-1], radbins[1:]):
        mask = (r < bhigh) * (r > blow)
        az, zz = radial_average(
            image, center=center, mask=mask, return_az=True, **kwargs
        )
        radavlist.append(zz)

    return radbins, az, radavlist

